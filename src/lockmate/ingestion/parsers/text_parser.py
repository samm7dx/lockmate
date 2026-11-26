"""Plain-text parsing."""

from pathlib import Path
from typing import Union, Iterator, Any, Optional
import structlog
from pydantic import BaseModel, ConfigDict

logger = structlog.get_logger()


class TextParserConfig(BaseModel):
    """Configuration for text parser."""
    model_config = ConfigDict(arbitrary_types_allowed=True)
    
    encoding: str = "utf-8"
    line_mode: str = "lines"  # "lines", "paragraphs", "whole"
    max_line_length: int = 1024 * 1024  # 1MB per line
    skip_empty: bool = True
    strip_whitespace: bool = True


class TextParser:
    """Parses plain text files."""
    
    def __init__(self, config: Optional[TextParserConfig] = None) -> None:
        self.config = config or TextParserConfig()
    
    def parse(
        self, 
        file_path: Union[str, Path], 
        encoding: Optional[str] = None
    ) -> Iterator[dict[str, Any]]:
        """
        Parse a plain text file.
        
        Args:
            file_path: Path to text file
            encoding: File encoding
            
        Yields:
            Dict with text content and metadata
        """
        file_path = Path(file_path)
        enc = encoding or self.config.encoding
        
        logger.info("text.parse_started", path=str(file_path), encoding=enc, mode=self.config.line_mode)
        
        try:
            if self.config.line_mode == "lines":
                yield from self._parse_lines(file_path, enc)
            elif self.config.line_mode == "paragraphs":
                yield from self._parse_paragraphs(file_path, enc)
            elif self.config.line_mode == "whole":
                yield from self._parse_whole(file_path, enc)
            else:
                raise ValueError(f"Unknown line_mode: {self.config.line_mode}")
                
        except UnicodeDecodeError as e:
            logger.error("text.encoding_error", path=str(file_path), error=str(e))
            raise
        
        logger.info("text.parse_completed", path=str(file_path))
    
    def _parse_lines(
        self, 
        file_path: Path, 
        encoding: str
    ) -> Iterator[dict[str, Any]]:
        """Parse file line by line."""
        line_number = 0
        
        with open(file_path, "r", encoding=encoding) as f:
            for line in f:
                line_number += 1
                
                if self.config.strip_whitespace:
                    line = line.rstrip("\n\r").strip()
                else:
                    line = line.rstrip("\n\r")
                
                if self.config.skip_empty and not line:
                    continue
                
                if len(line) > self.config.max_line_length:
                    logger.warning(
                        "text.line_too_long", 
                        path=str(file_path), 
                        line=line_number, 
                        length=len(line)
                    )
                    line = line[:self.config.max_line_length]
                
                yield {
                    "text": line,
                    "line_number": line_number,
                    "char_count": len(line),
                }
    
    def _parse_paragraphs(
        self, 
        file_path: Path, 
        encoding: str
    ) -> Iterator[dict[str, Any]]:
        """Parse file by paragraphs (separated by blank lines)."""
        para_number = 0
        current_para = []
        
        with open(file_path, "r", encoding=encoding) as f:
            for line in f:
                stripped = line.strip()
                
                if not stripped:
                    # Blank line - end of paragraph
                    if current_para:
                        para_number += 1
                        text = "\n".join(current_para)
                        if self.config.strip_whitespace:
                            text = text.strip()
                        
                        yield {
                            "text": text,
                            "paragraph_number": para_number,
                            "line_count": len(current_para),
                            "char_count": len(text),
                        }
                        current_para = []
                else:
                    current_para.append(line.rstrip("\n\r"))
            
            # Last paragraph
            if current_para:
                para_number += 1
                text = "\n".join(current_para)
                if self.config.strip_whitespace:
                    text = text.strip()
                
                yield {
                    "text": text,
                    "paragraph_number": para_number,
                    "line_count": len(current_para),
                    "char_count": len(text),
                }
    
    def _parse_whole(
        self, 
        file_path: Path, 
        encoding: str
    ) -> Iterator[dict[str, Any]]:
        """Parse entire file as single record."""
        with open(file_path, "r", encoding=encoding) as f:
            text = f.read()
        
        if self.config.strip_whitespace:
            text = text.strip()
        
        yield {
            "text": text,
            "file_name": file_path.name,
            "char_count": len(text),
            "line_count": text.count("\n") + 1,
        }