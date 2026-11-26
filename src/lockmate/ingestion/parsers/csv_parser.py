"""CSV and TSV parsing."""

from pathlib import Path
from typing import Union, Iterator, Optional, Any
from dataclasses import dataclass
import csv
import io
import structlog
from pydantic import BaseModel, Field, ConfigDict

logger = structlog.get_logger()


class CSVParserConfig(BaseModel):
    """Configuration for CSV/TSV parser."""
    model_config = ConfigDict(arbitrary_types_allowed=True)
    
    delimiter: str = ","
    quotechar: str = '"'
    escapechar: Optional[str] = None
    has_header: bool = True
    encoding: str = "utf-8"
    max_rows: Optional[int] = None
    skip_blank_rows: bool = True
    strict: bool = False


class CSVParser:
    """Parses CSV and TSV files securely."""
    
    def __init__(self, config: Optional[CSVParserConfig] = None) -> None:
        self.config = config or CSVParserConfig()
    
    def parse(
        self, 
        file_path: Union[str, Path], 
        encoding: Optional[str] = None
    ) -> Iterator[dict[str, Any]]:
        """
        Parse a CSV/TSV file.
        
        Args:
            file_path: Path to CSV/TSV file
            encoding: File encoding (overrides config)
            
        Yields:
            Dict representing each row
        """
        file_path = Path(file_path)
        enc = encoding or self.config.encoding
        
        logger.info("csv.parse_started", path=str(file_path), encoding=enc)
        
        row_count = 0
        
        try:
            with open(file_path, "r", encoding=enc, newline="") as f:
                # Detect delimiter for TSV
                if self.config.delimiter == "\t" or file_path.suffix.lower() == ".tsv":
                    dialect = csv.excel_tab
                else:
                    dialect = csv.excel
                
                reader = csv.DictReader(
                    f,
                    delimiter=self.config.delimiter,
                    quotechar=self.config.quotechar,
                    escapechar=self.config.escapechar,
                    dialect=dialect,
                    strict=self.config.strict,
                )
                
                for row in reader:
                    if self.config.skip_blank_rows and not any(row.values()):
                        continue
                    
                    # Add row number metadata
                    row_count += 1
                    row["_row_number"] = row_count
                    
                    yield row
                    
                    if self.config.max_rows and row_count >= self.config.max_rows:
                        break
                        
        except UnicodeDecodeError as e:
            logger.error("csv.encoding_error", path=str(file_path), error=str(e))
            raise
        except csv.Error as e:
            logger.error("csv.parse_error", path=str(file_path), error=str(e))
            raise
        
        logger.info("csv.parse_completed", path=str(file_path), rows=row_count)


class TSVParser(CSVParser):
    """Parses TSV files (Tab-Separated Values)."""
    
    def __init__(self, config: Optional[CSVParserConfig] = None) -> None:
        cfg = config or CSVParserConfig()
        cfg.delimiter = "\t"
        super().__init__(cfg)


# Convenience function for auto-detection
def parse_delimited(
    file_path: Union[str, Path],
    encoding: str = "utf-8"
) -> Iterator[dict[str, Any]]:
    """
    Auto-detect delimiter and parse.
    
    Args:
        file_path: Path to file
        encoding: File encoding
        
    Yields:
        Dict representing each row
    """
    file_path = Path(file_path)
    
    # Peek at first line to detect delimiter
    with open(file_path, "r", encoding=encoding) as f:
        first_line = f.readline()
    
    # Count delimiters
    comma_count = first_line.count(",")
    tab_count = first_line.count("\t")
    semicolon_count = first_line.count(";")
    pipe_count = first_line.count("|")
    
    counts = {
        ",": comma_count,
        "\t": tab_count,
        ";": semicolon_count,
        "|": pipe_count,
    }
    
    delimiter = max(counts, key=counts.get)
    
    config = CSVParserConfig(delimiter=delimiter, encoding=encoding)
    parser = CSVParser(config)
    
    yield from parser.parse(file_path, encoding=encoding)