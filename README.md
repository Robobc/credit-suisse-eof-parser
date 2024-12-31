# PDF Bank Transaction Parser

A Python script that extracts banking transactions from PDF bank statements and converts them into structured JSON format. The script handles multi-page PDF documents and automatically categorizes transactions as debits or credits based on balance changes.

## Features

- Extracts transactions from PDF bank statements
- Handles multi-page PDF documents
- Automatically categorizes transactions as debits or credits
- Validates and cleans transaction data
- Generates structured JSON output
- Comprehensive error handling and logging
- Supports DD.MM.YY date format
- Handles thousands separators in amounts

## Prerequisites

### Python Version
- Python 3.7 or higher

### Required Python Packages
```bash
pip install pdfplumber
