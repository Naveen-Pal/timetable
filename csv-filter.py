import pandas as pd
import re
import argparse

def process_timetable(input_file='Timetable.csv', output_file='Updated_Processed_Timetable.csv'):
    # Load the uploaded file
    df = pd.read_csv(input_file)

    df = df[df['Course Number'].str.len() <= 15]
    column_names = list(df.columns)

    df = df.drop_duplicates(subset=['Course Number'], keep='first')

    df = df[['Course Name', 'Course Number', 'Lecture', 'Tutorial', 'Lab', 'C']]
    df.columns = ['Course Name', 'Course Number', 'Lecture Time', 'Tutorial Time', 'Lab Time', 'Credit']

    def extract_location(text):
        if not isinstance(text, str):
            return text, ""
        
        locations = re.findall(r'\((.*?)\)', text)
        location = ", ".join([loc for loc in locations if len(loc) < 30])
        clean_text = re.sub(r'\(.*?\)', '', text).strip()
        
        return clean_text, location

    df['Lecture Location'] = ""
    df['Tutorial Location'] = ""
    df['Lab Location'] = ""

    for col, loc_col in [('Lecture Time', 'Lecture Location'), 
                         ('Tutorial Time', 'Tutorial Location'), 
                         ('Lab Time', 'Lab Location')]:
        df[[col, loc_col]] = pd.DataFrame(df[col].apply(extract_location).tolist(), index=df.index)

    df.reset_index(drop=True, inplace=True)
    df.to_csv(output_file, index=False)
    print(f"Processed timetable saved to {output_file}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Process timetable data')
    parser.add_argument('--input', default='Timetable.csv', help='Input CSV file path')
    parser.add_argument('--output', default='Updated_Processed_Timetable.csv', help='Output CSV file path')
    args = parser.parse_args()
    
    process_timetable(args.input, args.output)

