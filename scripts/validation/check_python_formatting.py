"""Verify that two Python sources have equal syntax trees and comments."""

import argparse
import ast
import io
import tokenize
from pathlib import Path


def syntax_and_comments(path):
    source = Path(path).read_text(encoding="utf-8")
    syntax = ast.dump(ast.parse(source, type_comments=True), include_attributes=False)
    comments = [
        token.string
        for token in tokenize.generate_tokens(io.StringIO(source).readline)
        if token.type == tokenize.COMMENT
    ]
    return syntax, comments


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("before")
    parser.add_argument("after")
    args = parser.parse_args()
    if syntax_and_comments(args.before) != syntax_and_comments(args.after):
        parser.exit(1, "FAIL: Python syntax or comments changed\n")
    print("PASS: Python syntax and comments are unchanged")
