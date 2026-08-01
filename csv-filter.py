import pandas as pd
import re
import argparse

def process_timetable(input_file='Timetable.csv', output_file='Updated_Processed_Timetable.csv'):
    # Load the uploaded file
    df = pd.read_csv(input_file)

    df = df[df['Course Number'].str.len() <= 15]
    column_names = list(df.columns)

    df = df.drop_duplicates(subset=['Course Number'], keep='first')

    df = df[['Course Name', 'Course Number', 'Lecture', 'Tutorial', 'Lab', 'C', 'Name of the Instructors and Tutors', 'Link To Course Plan']]
    df.columns = ['Course Name', 'Course Number', 'Lecture Time', 'Tutorial Time', 'Lab Time', 'Credit', 'Instructor', 'Course Plan']

    def extract_location(text):
        if not isinstance(text, str):
            return text, ""
        
        locations = re.findall(r'\((.*?)\)', text)
        location = ", ".join([loc if len(loc) < 30 else loc[:27]+"..." for loc in locations])
        clean_text = re.sub(r'\(.*?\)', '', text).strip()
        clean_text = clean_text.replace('\n', ', ')
        
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


def extract_slots(text):
    if pd.isna(text):
        return set()
    slots = set()
    for part in str(text).split('\n'):
        before_paren = part.split('(')[0]
        for s in before_paren.replace(',', ' ').split():
            s = s.strip()
            if re.match(r'^[A-Z]+\d+$', s):
                slots.add(s)
    return slots

def get_available_courses(selected_courses, file_path='Timetable.csv'):
    try:
        df = pd.read_csv(file_path)
    except FileNotFoundError:
        return []

    # 1. Determine which slots are occupied by selected courses
    occupied_slots = set()
    for course in selected_courses:
        course_rows = df[df['Course Number'] == course]
        for _, row in course_rows.iterrows():
            lec = extract_slots(row.get('Lecture'))
            tut = extract_slots(row.get('Tutorial'))
            lab = extract_slots(row.get('Lab'))
            occupied_slots.update(lec | tut | lab)
            
    # 2. Get all possible slots in the timetable
    all_slots = set()
    for _, row in df.iterrows():
        lec = extract_slots(row.get('Lecture'))
        tut = extract_slots(row.get('Tutorial'))
        lab = extract_slots(row.get('Lab'))
        all_slots.update(lec | tut | lab)
        
    # 3. Calculate empty slots
    empty_slots = all_slots - occupied_slots
    
    # 4. Find courses that fit
    available = []
    for _, row in df.iterrows():
        if row['Course Number'] in selected_courses:
            continue
            
        lec = extract_slots(row.get('Lecture'))
        tut = extract_slots(row.get('Tutorial'))
        lab = extract_slots(row.get('Lab'))
        req_slots = lec | tut | lab
        
        if req_slots and req_slots.issubset(empty_slots):
            available.append({
                'code': row['Course Number'],
                'name': row['Course Name']
            })
            
    return available


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", default="Timetable.csv")
    parser.add_argument("--output", default="Updated_Processed_Timetable.csv")
    args = parser.parse_args()
    process_timetable(args.input, args.output)