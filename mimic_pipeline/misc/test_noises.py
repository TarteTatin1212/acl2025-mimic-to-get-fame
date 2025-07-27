import csv
import argparse
from noises import CharacterNoiseApplier, WordNoiseApplier, SentenceNoiseApplier

INPUT_FILE = './output/new/English_Natural Language Processing_generated_meeting_results.csv'
OUTPUT_FILE = f"./noisy_output/Noises_{INPUT_FILE.split('/')[-1]}"

def read_csv(file_path):
    with open(file_path, 'r', newline='', encoding='utf-8') as csvfile:
        reader = csv.DictReader(csvfile)
        return list(reader)

def write_csv(file_path, data, fieldnames):
    with open(file_path, 'w', newline='', encoding='utf-8') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(data)

def apply_noise(text, noise_type, noise_level, noise_options):
    if noise_type == 'character':
        applier = CharacterNoiseApplier(
            swap_prob=noise_level,
            substitution_prob=noise_level,
            deletion_prob=noise_level / 2,
            insertion_prob=noise_level / 2,
            enabled_transforms=noise_options
        )
    elif noise_type == 'word':
        applier = WordNoiseApplier(
            noise_types=noise_options,
            noise_level=noise_level
        )
    elif noise_type == 'sentence':
        applier = SentenceNoiseApplier(
            noise_types=noise_options,
            noise_level=noise_level
        )
    else:
        raise ValueError(f"Unknown noise type: {noise_type}")
    
    return applier.apply_noise_to_transcript(text)

def process_csv(input_file, output_file, noise_type, noise_level, noise_options):
    data = read_csv(input_file)
    fieldnames = ['Title', 'Article', 'Tags', 'Personas', 'Summary', 'Meeting Plan', 'Meeting', 'Noisy Meeting']

    for row in data:
        if 'Meeting' in row:
            row['Noisy Meeting'] = apply_noise(row['Meeting'], noise_type, noise_level, noise_options)
    
    output_file = '/'.join(output_file.split('/')[:-1]) + '/' + noise_type + output_file.split('/')[-1]

    write_csv(output_file, data, fieldnames)

def main():
    parser = argparse.ArgumentParser(description="Apply noise to meeting transcripts.")
    parser.add_argument("--input_file", help="Path to the input CSV file", default=INPUT_FILE)
    parser.add_argument("--output_file", help="Path to the output CSV file", default=OUTPUT_FILE)
    parser.add_argument("--noise_type", choices=['character', 'word', 'sentence'], help="Type of noise to apply", default='character')
    parser.add_argument("--noise_level", type=float, default=0.3, help="Noise level (0.0 to 1.0)")
    parser.add_argument("--noise_options", nargs='*', help="Noise options (e.g., 'swap substitute' for character noise)")

    args = parser.parse_args()

    process_csv(args.input_file, args.output_file, args.noise_type, args.noise_level, args.noise_options)
    print(f"Noise applied to 'Meeting' column. Output written to {args.output_file}")

if __name__ == "__main__":
    main()