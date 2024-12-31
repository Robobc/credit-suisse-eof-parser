import pdfplumber
import json
import re
from decimal import Decimal, InvalidOperation
from typing import List, Dict, Optional
from pathlib import Path
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def is_numeric(value: str) -> bool:
    """Check if a string value can be converted to a decimal number."""
    try:
        cleaned_value = value.replace(',', '').replace("'", "").strip()
        if cleaned_value:
            Decimal(cleaned_value)
            return True
        return False
    except (InvalidOperation, AttributeError):
        return False

def clean_amount(value: str) -> str:
    """Clean and format amount strings."""
    return value.replace("'", "").replace(",", "").strip()

def is_date(text: str) -> bool:
    """Check if text matches date format DD.MM.YY"""
    return bool(re.match(r'^\d{2}\.\d{2}\.\d{2}$', text))

def extract_transaction_data(line: str) -> Optional[Dict[str, str]]:
    """Extract transaction data from a single line."""
    parts = line.split()
    if len(parts) < 3:
        return None
        
    # Check if the line starts with a date
    if not is_date(parts[0]):
        return None
        
    # Get the last numeric value as balance
    balance = None
    balance_index = -1
    
    for i, part in enumerate(reversed(parts)):
        if is_numeric(part):
            balance = clean_amount(part)
            balance_index = len(parts) - 1 - i
            break
            
    if not balance:
        return None
        
    # Look for transaction amount (debit or credit)
    amount = None
    amount_index = -1
    
    for i in range(balance_index - 1, 0, -1):
        if i >= len(parts):
            continue
        if is_numeric(parts[i]):
            amount = clean_amount(parts[i])
            amount_index = i
            break
            
    # Extract description (everything between date and amount)
    description_parts = parts[1:amount_index] if amount_index > 0 else parts[1:balance_index]
    description = ' '.join(description_parts).strip()
    
    return {
        "date": parts[0],
        "description": description,
        "amount": amount,
        "balance": balance
    }

def parse_pdf(file_path: str) -> List[Dict[str, str]]:
    """Parse transactions from a PDF file."""
    transactions = []
    pdf_path = Path(file_path)
    
    if not pdf_path.exists():
        raise FileNotFoundError(f"PDF file not found: {file_path}")
    
    try:
        with pdfplumber.open(pdf_path) as pdf:
            if not pdf.pages:
                raise ValueError("PDF file is empty")
            
            prev_balance = None
            
            for page_num, page in enumerate(pdf.pages, 1):
                text = page.extract_text()
                if not text:
                    logger.warning(f"No text found on page {page_num}")
                    continue
                
                # Split text into lines and process each line
                lines = text.split('\n')
                for line_num, line in enumerate(lines, 1):
                    try:
                        transaction_data = extract_transaction_data(line)
                        if not transaction_data:
                            continue
                            
                        current_balance = Decimal(transaction_data['balance'])
                        amount = Decimal(transaction_data['amount']) if transaction_data['amount'] else None
                        
                        # Determine debit/credit
                        debit = ''
                        credit = ''
                        
                        if prev_balance is not None and amount is not None:
                            if current_balance > prev_balance:
                                credit = str(amount)
                            else:
                                debit = str(amount)
                        
                        transaction = {
                            "Date": transaction_data['date'],
                            "Description": transaction_data['description'],
                            "Debit": debit,
                            "Credit": credit,
                            "Balance": transaction_data['balance']
                        }
                        
                        transactions.append(transaction)
                        prev_balance = current_balance
                        
                    except Exception as e:
                        logger.error(f"Error processing line {line_num} on page {page_num}: {str(e)}\nLine content: {line}")
                        continue
                        
    except Exception as e:
        logger.error(f"Error processing PDF file: {str(e)}")
        raise
        
    return transactions

def validate_transactions(transactions: List[Dict[str, str]]) -> List[Dict[str, str]]:
    """Validate and fix transactions data."""
    validated_transactions = []
    prev_balance = None
    
    for transaction in transactions:
        try:
            # Ensure all required fields exist
            date = transaction.get('Date', '').strip()
            description = transaction.get('Description', '').strip()
            balance = transaction.get('Balance', '').strip()
            
            if not all([date, description, balance]):
                continue
                
            current_balance = Decimal(balance)
            debit = transaction.get('Debit', '').strip()
            credit = transaction.get('Credit', '').strip()
            
            # If amount fields are empty but we have a balance change
            if prev_balance is not None:
                balance_diff = abs(current_balance - prev_balance)
                
                if not (debit or credit):  # If both are empty
                    if current_balance < prev_balance:
                        debit = str(balance_diff)
                        credit = ''
                    elif current_balance > prev_balance:
                        credit = str(balance_diff)
                        debit = ''
            
            validated_transaction = {
                "Date": date,
                "Description": description,
                "Debit": debit,
                "Credit": credit,
                "Balance": balance
            }
            
            validated_transactions.append(validated_transaction)
            prev_balance = current_balance
            
        except (InvalidOperation, ValueError) as e:
            logger.error(f"Error validating transaction: {str(e)}")
            continue
            
    return validated_transactions

def save_transactions(transactions: List[Dict[str, str]], output_file: str) -> None:
    """Save transactions to JSON file with proper formatting."""
    try:
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(transactions, f, indent=2, ensure_ascii=False)
        logger.info(f"Successfully saved {len(transactions)} transactions to {output_file}")
    except Exception as e:
        logger.error(f"Error saving transactions: {str(e)}")
        raise

def main():
    """Main execution function"""
    try:
        pdf_file = "2278524-60_extract_of_account_2024-01-13_00-55-03961.pdf"
        output_json = "transactions.json"
        
        # Parse PDF and get initial transactions
        raw_transactions = parse_pdf(pdf_file)
        logger.info(f"Initially parsed {len(raw_transactions)} transactions")
        
        # Validate and fix transactions
        validated_transactions = validate_transactions(raw_transactions)
        logger.info(f"Validated {len(validated_transactions)} transactions")
        
        # Save final transactions
        save_transactions(validated_transactions, output_json)
        
    except Exception as e:
        logger.error(f"Program failed: {str(e)}")
        raise

if __name__ == "__main__":
    main()
