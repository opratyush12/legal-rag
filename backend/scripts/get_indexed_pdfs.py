"""
Extract the list of PDF files actually used in your index
"""

import pickle
import pandas as pd
from pathlib import Path

def get_indexed_pdfs():
    """Get unique PDF names from your metadata"""
    
    index_store_path = Path(__file__).parent.parent / "index_store"
    metadata_path = index_store_path / "metadata.pkl"
    
    if not metadata_path.exists():
        print(f"❌ Metadata file not found at {metadata_path}")
        return None
    
    print(f"📂 Loading metadata from: {metadata_path}")
    
    with open(metadata_path, 'rb') as f:
        metadata = pickle.load(f)
    
    pdfs = set()
    for item in metadata:
        pdfs.add(item['pdf_index'])
    
    print(f"\n✅ Your index references {len(pdfs)} unique PDFs")
    
    output_dir = Path(__file__).parent.parent / "index_store"
    with open(output_dir / 'indexed_pdfs.txt', 'w') as f:
        for pdf in sorted(pdfs):
            f.write(f"{pdf}\n")
    
    df = pd.DataFrame(list(pdfs), columns=['pdf_index'])
    df.to_csv(output_dir / 'indexed_pdfs.csv', index=False)
    
    return pdfs

def check_missing_pdfs(pdfs, pdf_directory):
    pdf_dir = Path(pdf_directory)
    existing = []
    missing = []
    
    print(f"\n🔍 Checking PDF directory: {pdf_dir}")
    
    if not pdf_dir.exists():
        print(f"❌ Directory not found: {pdf_dir}")
        return [], pdfs
    
    for pdf in pdfs:
        pdf_path = pdf_dir / pdf
        if pdf_path.exists():
            existing.append(pdf)
        else:
            missing.append(pdf)
    
    print(f"\n📊 Results:")
    print(f"   ✅ Existing PDFs: {len(existing)}")
    print(f"   ❌ Missing PDFs: {len(missing)}")
    
    return existing, missing

if __name__ == "__main__":
    print("=" * 60)
    pdfs = get_indexed_pdfs()
    
    if pdfs:
        pdf_directory = r"C:\Users\PratyushOjha\Documents\projectPractice\supream_court_data\processed_data"
        existing, missing = check_missing_pdfs(pdfs, pdf_directory)
        
        print("\n" + "=" * 60)
        print(f"   PDFs to upload to S3: {len(existing)}")
