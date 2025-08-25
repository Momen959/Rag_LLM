from src.config.settings import get_settings
import re



def clean_text(text):
    text = text.replace("\xa0", " ")

    # Remove non-printable/control characters
    text = re.sub(r"[^\x20-\x7E\n]+", " ", text)

    # Replace multiple spaces with one
    text = re.sub(r" {2,}", " ", text)

    # Replace multiple newlines with a single newline
    text = re.sub(r"\n{2,}", "\n", text)

    # Strip leading/trailing whitespace
    text = text.strip()

    return text



def chunker(text, size=get_settings().CHUNK_SIZE, overlap=get_settings().OVERLAP):
    cleaned_text = clean_text(text)
    seq = cleaned_text.split()
    chunks = []
    start = 0
    while start < len(seq):
        end = start + size
        chunk = seq[start:end]
        chunks.append(" ".join(chunk))


        if end >= len(seq):
            break


        start+= size - overlap
    return chunks