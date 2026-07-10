#!/usr/bin/env python3
"""Validate an arbitrary JSON object against a JSON Schema.

Standalone: uses only the Python standard library (``json``, ``re``) — no
external dependency such as ``jsonschema`` is required.

Supported keywords (covers the proposalgenerator schemas, both Draft-07 and
Draft 2020-12 dialects):

    Structure : type (incl. union arrays like ["string", "null"]),
                properties, required, additionalProperties (bool or schema),
                items, $ref (local JSON pointers: #/$defs/... , #/definitions/...)
    Values    : enum, const
    Numbers   : minimum, maximum, exclusiveMinimum, exclusiveMaximum, multipleOf
    Strings   : minLength, maxLength, pattern
    Arrays    : minItems, maxItems, uniqueItems
    Composition (bonus): allOf, anyOf, oneOf, not
    Annotations (ignored): title, description, $schema, $id, default, examples

A boolean schema (``true`` / ``false``) is honoured. Unknown keywords are
ignored, matching JSON Schema's open-world behaviour.

Usage:
    # JSON object via stdin (the "raw input text" case)
    echo '{"foo": 1}' | python3 validate_json.py /abs/path/to/schema.json

    # JSON object as a second argument
    python3 validate_json.py /abs/path/to/schema.json '{"foo": 1}'

    # JSON object from a file
    python3 validate_json.py /abs/path/to/schema.json --instance-file /abs/data.json

Exit codes:
    0  valid
    1  invalid (schema violation)
    2  usage / parsing / IO error
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any


# --------------------------------------------------------------------------- #
# Validator
# --------------------------------------------------------------------------- #

class SchemaError(Exception):
    """The schema itself is malformed (not the instance)."""


class Validator:
    """A minimal JSON Schema validator built on the standard library only."""

    def __init__(self, root_schema: Any) -> None:
        self.root = root_schema

    def validate(self, instance: Any) -> list[str]:
        """Return a list of human-readable error strings (empty == valid)."""
        errors: list[str] = []
        self._validate(instance, self.root, [], errors)
        return errors

    # -- core recursion ---------------------------------------------------- #

    def _validate(self, inst: Any, schema: Any, path: list[Any], errors: list[str]) -> None:
        # Boolean schemas.
        if schema is True:
            return
        if schema is False:
            errors.append(self._err(path, "no value is allowed here (schema is false)"))
            return
        if not isinstance(schema, dict):
            raise SchemaError(f"schema fragment at {self._ptr(path)} is not an object or boolean")

        # $ref replaces validation with the referenced schema (sibling keywords
        # in our schemas are annotations only, so ignoring them is safe).
        if "$ref" in schema:
            resolved = self._resolve_ref(schema["$ref"])
            self._validate(inst, resolved, path, errors)
            return

        # Composition.
        for key in ("allOf", "anyOf", "oneOf"):
            if key in schema:
                self._validate_composition(key, inst, schema[key], path, errors)
        if "not" in schema:
            sub: list[str] = []
            self._validate(inst, schema["not"], path, sub)
            if not sub:
                errors.append(self._err(path, "value must NOT match the 'not' subschema, but it does"))

        # type
        if "type" in schema:
            self._check_type(inst, schema["type"], path, errors)

        # enum / const
        if "enum" in schema and inst not in schema["enum"]:
            errors.append(self._err(path, f"value {inst!r} is not one of the allowed values {schema['enum']!r}"))
        if "const" in schema and inst != schema["const"]:
            errors.append(self._err(path, f"value {inst!r} must equal the constant {schema['const']!r}"))

        # Type-specific keyword groups.
        if isinstance(inst, dict):
            self._check_object(inst, schema, path, errors)
        if isinstance(inst, list):
            self._check_array(inst, schema, path, errors)
        if isinstance(inst, str):
            self._check_string(inst, schema, path, errors)
        # bool is a subclass of int in Python — exclude it from number checks.
        if isinstance(inst, (int, float)) and not isinstance(inst, bool):
            self._check_number(inst, schema, path, errors)

    # -- composition ------------------------------------------------------- #

    def _validate_composition(self, key, inst, subschemas, path, errors):
        if not isinstance(subschemas, list):
            raise SchemaError(f"'{key}' at {self._ptr(path)} must be an array")
        match_count = 0
        collected: list[str] = []
        for sub in subschemas:
            sub_errors: list[str] = []
            self._validate(inst, sub, path, sub_errors)
            if not sub_errors:
                match_count += 1
            else:
                collected.extend(sub_errors)
        if key == "allOf" and match_count != len(subschemas):
            errors.extend(collected)
        elif key == "anyOf" and match_count == 0:
            errors.append(self._err(path, "value does not match any subschema in 'anyOf'"))
        elif key == "oneOf" and match_count != 1:
            errors.append(self._err(path, f"value must match exactly one subschema in 'oneOf' (matched {match_count})"))

    # -- type -------------------------------------------------------------- #

    def _check_type(self, inst, types, path, errors):
        allowed = types if isinstance(types, list) else [types]
        if not any(self._is_type(inst, t) for t in allowed):
            got = self._json_type(inst)
            want = " or ".join(str(t) for t in allowed)
            errors.append(self._err(path, f"expected type {want}, got {got}"))

    @staticmethod
    def _is_type(inst, t) -> bool:
        if t == "null":
            return inst is None
        if t == "boolean":
            return isinstance(inst, bool)
        if t == "object":
            return isinstance(inst, dict)
        if t == "array":
            return isinstance(inst, list)
        if t == "string":
            return isinstance(inst, str)
        if t == "number":
            return isinstance(inst, (int, float)) and not isinstance(inst, bool)
        if t == "integer":
            if isinstance(inst, bool):
                return False
            if isinstance(inst, int):
                return True
            return isinstance(inst, float) and inst.is_integer()
        raise SchemaError(f"unknown type keyword {t!r}")

    @staticmethod
    def _json_type(inst) -> str:
        if inst is None:
            return "null"
        if isinstance(inst, bool):
            return "boolean"
        if isinstance(inst, str):
            return "string"
        if isinstance(inst, dict):
            return "object"
        if isinstance(inst, list):
            return "array"
        if isinstance(inst, int):
            return "integer"
        if isinstance(inst, float):
            return "number"
        return type(inst).__name__

    # -- objects ----------------------------------------------------------- #

    def _check_object(self, inst, schema, path, errors):
        props = schema.get("properties", {})
        for req in schema.get("required", []):
            if req not in inst:
                errors.append(self._err(path, f"missing required property '{req}'"))

        for name, value in inst.items():
            if name in props:
                self._validate(value, props[name], path + [name], errors)
            else:
                addl = schema.get("additionalProperties", True)
                if addl is False:
                    errors.append(self._err(path + [name], f"additional property '{name}' is not allowed"))
                elif isinstance(addl, (dict, bool)) and addl is not True:
                    self._validate(value, addl, path + [name], errors)

        for bound, op, label in (("minProperties", "<", "at least"), ("maxProperties", ">", "at most")):
            if bound in schema:
                n = len(inst)
                limit = schema[bound]
                if (op == "<" and n < limit) or (op == ">" and n > limit):
                    errors.append(self._err(path, f"object must have {label} {limit} properties, has {n}"))

    # -- arrays ------------------------------------------------------------ #

    def _check_array(self, inst, schema, path, errors):
        if "items" in schema:
            item_schema = schema["items"]
            for i, item in enumerate(inst):
                self._validate(item, item_schema, path + [i], errors)
        if "minItems" in schema and len(inst) < schema["minItems"]:
            errors.append(self._err(path, f"array must have at least {schema['minItems']} items, has {len(inst)}"))
        if "maxItems" in schema and len(inst) > schema["maxItems"]:
            errors.append(self._err(path, f"array must have at most {schema['maxItems']} items, has {len(inst)}"))
        if schema.get("uniqueItems") is True:
            seen: list[Any] = []
            for item in inst:
                if item in seen:
                    errors.append(self._err(path, f"array items must be unique; {item!r} is duplicated"))
                    break
                seen.append(item)

    # -- strings ----------------------------------------------------------- #

    def _check_string(self, inst, schema, path, errors):
        if "minLength" in schema and len(inst) < schema["minLength"]:
            errors.append(self._err(path, f"string is shorter than minLength {schema['minLength']}"))
        if "maxLength" in schema and len(inst) > schema["maxLength"]:
            errors.append(self._err(path, f"string is longer than maxLength {schema['maxLength']}"))
        if "pattern" in schema:
            try:
                if re.search(schema["pattern"], inst) is None:
                    errors.append(self._err(path, f"string does not match pattern {schema['pattern']!r}"))
            except re.error as exc:
                raise SchemaError(f"invalid regex in 'pattern' at {self._ptr(path)}: {exc}")

    # -- numbers ----------------------------------------------------------- #

    def _check_number(self, inst, schema, path, errors):
        if "minimum" in schema and inst < schema["minimum"]:
            errors.append(self._err(path, f"value {inst} is less than minimum {schema['minimum']}"))
        if "maximum" in schema and inst > schema["maximum"]:
            errors.append(self._err(path, f"value {inst} is greater than maximum {schema['maximum']}"))
        if "exclusiveMinimum" in schema and inst <= schema["exclusiveMinimum"]:
            errors.append(self._err(path, f"value {inst} must be > {schema['exclusiveMinimum']}"))
        if "exclusiveMaximum" in schema and inst >= schema["exclusiveMaximum"]:
            errors.append(self._err(path, f"value {inst} must be < {schema['exclusiveMaximum']}"))
        if "multipleOf" in schema:
            factor = schema["multipleOf"]
            quotient = inst / factor
            if abs(quotient - round(quotient)) > 1e-9:
                errors.append(self._err(path, f"value {inst} is not a multiple of {factor}"))

    # -- $ref resolution --------------------------------------------------- #

    def _resolve_ref(self, ref: Any) -> Any:
        if not isinstance(ref, str) or not ref.startswith("#"):
            raise SchemaError(f"only local $ref pointers are supported, got {ref!r}")
        pointer = ref[1:]
        if pointer in ("", "/"):
            return self.root
        node: Any = self.root
        for raw in pointer.lstrip("/").split("/"):
            token = raw.replace("~1", "/").replace("~0", "~")
            if isinstance(node, dict) and token in node:
                node = node[token]
            elif isinstance(node, list) and token.isdigit() and int(token) < len(node):
                node = node[int(token)]
            else:
                raise SchemaError(f"$ref {ref!r} cannot be resolved (missing '{token}')")
        return node

    # -- helpers ----------------------------------------------------------- #

    @staticmethod
    def _ptr(path: list[Any]) -> str:
        return "/" + "/".join(str(p) for p in path) if path else "<root>"

    def _err(self, path: list[Any], message: str) -> str:
        return f"at '{self._ptr(path)}': {message}"


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #

def _fail(message: str, code: int = 2):
    sys.stderr.write(f"{message}\n")
    sys.exit(code)


def load_schema(schema_path: str) -> Any:
    path = Path(schema_path)
    if not path.is_absolute():
        _fail(f"Schema path must be absolute: {schema_path}")
    if not path.is_file():
        _fail(f"Schema file not found: {schema_path}")
    try:
        with path.open(encoding="utf-8") as fh:
            return json.load(fh)
    except json.JSONDecodeError as exc:
        _fail(f"Schema is not valid JSON ({schema_path}): {exc}")
    except OSError as exc:
        _fail(f"Could not read schema file: {exc}")


def read_instance(args: argparse.Namespace) -> str:
    if args.instance_file:
        path = Path(args.instance_file)
        if not path.is_file():
            _fail(f"Instance file not found: {args.instance_file}")
        try:
            return path.read_text(encoding="utf-8")
        except OSError as exc:
            _fail(f"Could not read instance file: {exc}")
    if args.instance is not None:
        return args.instance
    if sys.stdin.isatty():
        _fail("No JSON instance provided. Pass it via stdin, as an argument, or with --instance-file.")
    return sys.stdin.read()


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Validate a JSON object against a JSON Schema (standard library only).",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("schema", help="Absolute path to the JSON Schema file.")
    parser.add_argument("instance", nargs="?", default=None,
                        help="JSON object as text. If omitted, read from stdin.")
    parser.add_argument("--instance-file", help="Read the JSON object from this file.")
    args = parser.parse_args()

    schema = load_schema(args.schema)

    raw = read_instance(args)
    try:
        instance = json.loads(raw)
    except json.JSONDecodeError as exc:
        _fail(f"Input is not valid JSON: {exc}")

    try:
        errors = Validator(schema).validate(instance)
    except SchemaError as exc:
        _fail(f"The schema itself is invalid: {exc}")

    if not errors:
        print("VALID: the JSON object conforms to the schema.")
        return 0

    print(f"INVALID: {len(errors)} error(s) found.\n")
    for i, msg in enumerate(errors, 1):
        print(f"{i}. {msg}")
    return 1


if __name__ == "__main__":
    sys.exit(main())
