import csv

# Configurable parameters
INPUT_FILE = "csv/in/2025-05-01_2025-05-31(1).csv"
MESSAGE_COLUMN = "message"
PATTERNS = [
    "",  # Add suspicious substrings here
]

SEP = '\t'
SAMPLE_LIMIT = 10  # Number of sample messages to display per pattern

def find_exact_patterns():
    # Initialize counts and samples
    counts = {pat: 0 for pat in PATTERNS}
    samples = {pat: [] for pat in PATTERNS}

    # Read CSV and search
    with open(INPUT_FILE, encoding="utf-8") as f:
        reader = csv.DictReader(f, delimiter=SEP, quoting=csv.QUOTE_NONE)
        for row in reader:
            msg = row.get(MESSAGE_COLUMN, "")
            for pat in PATTERNS:
                # Strict substring search
                if pat in msg:
                    counts[pat] += 1
                    if len(samples[pat]) < SAMPLE_LIMIT:
                        samples[pat].append(msg)

    # Output results
    for pat in PATTERNS:
        print(f"Pattern: '{pat}'")
        print(f"Exact matches found: {counts[pat]}")
        if samples[pat]:
            print("Sample messages:")
            for s in samples[pat]:
                print(" -", s)
        print("-" * 60)

if __name__ == "__main__":
    find_exact_patterns()
