import pandas as pd


def extract_csv(file_path: str) -> str:
    df = pd.read_csv(file_path)

    return df.to_string(index=False)