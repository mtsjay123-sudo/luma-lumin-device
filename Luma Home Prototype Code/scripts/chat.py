#!/usr/bin/env python3
"""Compatibility launcher for the unified LUMA CLI."""
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from luma.cli import main
if __name__=='__main__':main()
