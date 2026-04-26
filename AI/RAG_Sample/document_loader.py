import PyPDF2
from pathlib import Path
from typing import List, Dict, Any
import re

class DocumentParser:
    """Parse PDF and Excel documents into chunks"""
    
    @staticmethod
    def parse_pdf(file_path: str) -> List[str]:
        """Extract text from PDF"""
        texts = []
        try:
            with open(file_path, 'rb') as f:
                pdf_reader = PyPDF2.PdfReader(f)
                for page_num, page in enumerate(pdf_reader.pages):
                    text = page.extract_text()
                    if text.strip():
                        # Add page marker for context
                        texts.append(f"[Page {page_num + 1}]\n{text}")
        except Exception as e:
            print(f"Error parsing PDF {file_path}: {e}")
        return texts
    
    
    @staticmethod
    def chunk_text(texts: List[str], chunk_size=200, overlap=30) -> List[str]:
        chunks = []
        full_text = "\n".join(texts)
        paragraphs = full_text.split("\n")

        for para in paragraphs:
            if not para.strip():
                continue
                
            sentences = re.split(r'(?<=[.!?])\s+', para)

            current_chunk = []
            current_length = 0
            
            for sentence in sentences:
                words = sentence.split()

                if current_length + len(words) > chunk_size:
                    chunks.append(" ".join(current_chunk))

                    overlap_words = current_chunk[-overlap:] if overlap else []
                    current_chunk = overlap_words.copy()
                    current_length = len(current_chunk)

                current_chunk.extend(words)
                current_length += len(words)

            if current_chunk:
                chunks.append(" ".join(current_chunk))

        return chunks
    
    @staticmethod
    def load_and_process_documents(data_dir: str = ".") -> List[Dict[str, Any]]:
        """Load all documents from directory and return processed chunks"""
        documents = []
        data_path = Path(data_dir)
        
        # Process PDF files (search recursively in all subdirectories)
        for pdf_file in data_path.glob("**/*.pdf"):
            print(f"Processing PDF: {pdf_file.name}")
            texts = DocumentParser.parse_pdf(str(pdf_file))
            chunks = DocumentParser.chunk_text(texts)
            for chunk in chunks:
                documents.append({
                    "content": chunk,
                    "source": pdf_file.name,
                    "type": "pdf"
                })
        
        print(f"Loaded {len(documents)} document chunks")
        return documents
