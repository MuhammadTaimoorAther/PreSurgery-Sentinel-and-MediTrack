from flask import Flask, render_template, request, redirect, url_for, session
import firebase_admin
from firebase_admin import credentials
from firebase_admin import storage as firebase_storage
import os
import datetime
from firebase_admin import firestore
from werkzeug.utils import secure_filename
from flask import request, jsonify
from io import BytesIO
from PIL import Image
import numpy as np
import cv2
import pytesseract
import csv
from flask_session import Session
# Set the path to the Tesseract OCR executable
pytesseract.pytesseract.tesseract_cmd = r"C:\\Program Files\\Tesseract-OCR\\tesseract.exe"
# Set environment variable
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = r"E:\PSS-MT\Database\pre-surgery-sentinel-firebase-adminsdk-ebxei-69754c8299.json"

# Initialize Firebase Admin SDK with service account credentials
cred = credentials.Certificate(r"E:\PSS-MT\Database\pre-surgery-sentinel-firebase-adminsdk-ebxei-69754c8299.json")
firebase_admin.initialize_app(cred, {
    'storageBucket': 'pre-surgery-sentinel.appspot.com'
})

bucket = firebase_storage.bucket()
db = firestore.client()
app = Flask(__name__)

# Configure session to use a custom directory for storing session data
app.config['SESSION_FILE_DIR'] = '/path/to/your/desired/directory'
app.config['SESSION_TYPE'] = 'filesystem'
app.config['SECRET_KEY'] = 'your_secret_key'
Session(app)

@app.route('/')
def index():
    return render_template('index.html')


@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        # Extract form data
        name = request.form['name']
        email = request.form['email']
        password = request.form['password']
        age = request.form['age']
        gender = request.form['gender']
        role = request.form['role']

        if role == 'patient':
            doc_ref = db.collection('patients').document(email)
            doc_ref.set({
                'name': name,
                'email': email,
                'password': password,
                'age': age,
                'gender': gender,
                'role': role
            })
        elif role == 'doctor':

            doc_ref = db.collection('doctors').document(email)
            doc_ref.set({
                'name': name,
                'email': email,
                'password': password,
                'age': age,
                'gender': gender,
                'role': role
            })

        # Determine the redirect URL based on the role
        if role == 'patient':
            return redirect('/UserD')
        elif role == 'doctor':
            return redirect('/DoctorD')

    # If it's a GET request or if there's an error, render the signup form
    return render_template('signup.html')

from flask import url_for

@app.route('/signin', methods=['POST'])
def signin():
    email = request.form['email1']
    password = request.form['password1']
    role = request.form['role']

    if role == 'patient':
        collection_ref = db.collection('patients')
        success_redirect = url_for('user_success', email=email)
    elif role == 'doctor':
        collection_ref = db.collection('doctors')
        success_redirect = '/DoctorD'
    else:
        return "Invalid role"

    # Check if user exists in the specified collection
    user_doc = collection_ref.document(email).get()
    if user_doc.exists:
        # User exists, now check the password
        stored_password = user_doc.get('password')
        if password == stored_password:
            session['email'] = email
            session['role'] = role
            return redirect(success_redirect)
        else:
            return render_template('signup.html', error="Incorrect password")
    else:
        return "User not found"
@app.route('/UserD')
def user_success():
    # Get the user's email from the query parameters
    user_email = request.args.get('email')

    # Fetch user information from Firestore
    user_doc_ref = db.collection('patients').document(user_email)
    user_info = user_doc_ref.get().to_dict()

    return render_template('UserD.html', user_info=user_info)


# Route for rendering the success page for doctors
@app.route('/DoctorD')
def doctor_success():
    return render_template('DoctorD.html')


@app.route('/upload', methods=['POST'])
def upload_file():
    if 'fileUpload' not in request.files:
        return jsonify({'error': 'No file part'}), 400

    file = request.files['fileUpload']
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400

    report_name = request.form.get('reportName')
    if not report_name:
        return jsonify({'error': 'Report name is required'}), 400

    try:
        # Read the image data into memory
        image_data = BytesIO()
        file.save(image_data)

        process_image(image_data, report_name)

        return 'File uploaded successfully for report: ' + report_name, 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

def process_image(image_data, report_name):
    try:
        # Create a PIL image from the image data
        input_image = Image.open(image_data)
        output_image = r'E:\PSS-MT\txt&csv\contrast_adjusted_image_1.jpg'
        preprocess_image(input_image, output_image)
        extracted_text = extract_text_from_image(output_image)
        print("Text extracted from the report:", extracted_text)

        # Write the extracted text to the text files for each report
        outputdirectory =r'E:\PSS-MT\txt&csv\ '
        output_text_file = outputdirectory + report_name + '.txt'
        with open(output_text_file, 'w', encoding='utf-8') as file:
            file.write(extracted_text)
        print("Text extracted from report saved in", output_text_file)

        #for APTT File
        if report_name == 'Activated Partial Thromboplastin Time (aPTT)':
            #calling the function for text extraction
            aptt_info = extract_APTT_info(output_text_file)
            #text file to csv
            if aptt_info:
                print("Extracted APTT Information:")
                print(aptt_info)
                csv_file = outputdirectory + report_name + '.csv'
                store_info_to_csv_for_aptt(aptt_info, csv_file)

                # Read data from the CSV file for firebase
                csv_data = []
                with open(csv_file, 'r') as file:
                    reader = csv.DictReader(file)
                    print(reader)
                    for row in reader:
                        csv_data.append(row)

                # Get email from session
                email = session.get('email')

                if email:
                    # Create a new collection after the email document
                    collection_ref = db.collection('patients').document(email).collection('APTT')

                    # Store data from CSV in the new collection
                    for row in csv_data:
                        # Create a document for each test result
                        test_result = {
                            'Category': row['Category'],
                            'Result': row['Result'],
                            'Unit': row['Unit'],
                            'Reference_Range': row['Reference Range']
                        }
                        collection_ref.document('APTT_result').set(test_result)

                    return "CSV data uploaded successfully."
                else:
                    return "Email not found in session."
            else:
                return "aptt info not found"

        #same for CRP
        elif report_name=='C-reactive protein (CRP)':
            crp=extract_chemistry_info(output_text_file)
            #text file to csv
            if crp:
                print("Extracted CRP Information:")
                print(crp)
                csv_file = outputdirectory + report_name + '.csv'
                store_info_to_csv_for_CRP(crp,csv_file)

                csv_data = []

                with open(csv_file, 'r') as file:
                    reader = csv.DictReader(file)
                    print(reader)
                    for row in reader:
                        csv_data.append(row)
                # Get email from session
                email = session.get('email')

                if email:
                    # Create a new collection after the email document
                    collection_ref = db.collection('patients').document(email).collection('Chemistry')

                    # Store data from CSV in the new collection
                    for row in csv_data:
                        # Create a document for each test result
                        test_result = {
                            'Chemistry':row['Chemistry'],
                            'Unit': row['Unit'],
                            'Result': row['Result'],
                            'Reference_Range': row['Reference Range']
                        }

                        collection_ref.document('CRP_result').set(test_result)

                    return "Chemistry data uploaded successfully."
                else:
                    return "Email not found in session."
            else:
                return("crp info not found")
    finally:
        # Close the image data
        image_data.close()

# Function to preprocess the image

def preprocess_image(image, output_image):
    # Convert PIL image to OpenCV format
    image_cv2 = np.array(image)
    image_cv2 = image_cv2[:, :, ::-1].copy()  # Convert RGB to BGR

    # Convert the image to grayscale
    grayscale_image = cv2.cvtColor(image_cv2, cv2.COLOR_BGR2GRAY)

    # Apply contrast adjustment
    alpha = 1  # Adjust the alpha value as needed
    beta = 3.5  # Adjust the beta value as needed
    contrast_adjusted_image = cv2.convertScaleAbs(grayscale_image, alpha=alpha, beta=beta)

    # Save the contrast-adjusted image
    output_dir = r'E:\PSS-MT\txt&csv\ '  # Raw string to handle backslashes
    output_path = os.path.join(output_dir, output_image)
    cv2.imwrite(output_path, contrast_adjusted_image)

    print("Image converted to grayscale and contrast adjusted. Saved as", output_path)

# Function to extract text from the preprocessed image
def extract_text_from_image(image_path):
    # Open the preprocessed image using PIL (Pillow)
    img = Image.open(image_path)

    # Use pytesseract to extract text
    text = pytesseract.image_to_string(img)
    return text


def extract_APTT_info(file_path):
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            content = file.read()
            lines = content.split('\n')
            aptt_info = ""
            capturing_aptt = False

            for line in lines:
                if "APT Result Unit" in line:
                    capturing_aptt = True
                if capturing_aptt and ("Patient" in line or "Control" in line):
                    aptt_info += line.strip() + "\n"

            if aptt_info:
                print("File found here")
                return aptt_info.strip()
            else:
                print("APT Information not found in the file.")
                return None
    except Exception as e:
        print("An error occurred while extracting APTT information:", e)
        return None


def store_info_to_csv_for_aptt(extracted_info, csv_file):
    if not extracted_info:
        print("No data to store in CSV.")
        return

    try:
        lines = extracted_info.split('\n')
        variables = ['Category', 'Result', 'Unit',  'Reference Range']

        # Initialize variables to store patient and control values
        patient_values = []
        control_values = []

        # Extract patient and control values
        for line in lines:
            if "Patient" in line:
                patient_values = line.split()[1:]
            elif "Control" in line:
                control_values = line.split()[1:]

        # Check if both patient and control values are present
        if not patient_values or not control_values:
            print("Incomplete APTT information.")
            return

        with open(csv_file, 'w', newline='') as file:
            writer = csv.writer(file)
            writer.writerow(variables)
            writer.writerow(['Patient'] + patient_values)
            writer.writerow(['Control'] + control_values)

        print("Data stored in", csv_file)
    except Exception as e:
        print("An error occurred while storing data to CSV file:", e)

def extract_chemistry_info(file_path):
    # Open the text file and read its contents
    with open(file_path, 'r', encoding='utf-8') as file:
        content = file.read()

    # Split the content into lines
    lines = content.split('\n')

    # Initialize variables to store chemistry information
    chemistry_info = []

    # Flag to indicate when to start capturing chemistry information
    capturing_chemistry = False

    # Iterate through each line to find chemistry information
    for line in lines:
        # Start capturing chemistry information when the header line is found
        if "Chemistry Result Unit Reference Range" in line:
            capturing_chemistry = True
            continue

        # Stop capturing chemistry information when the next section starts
        if capturing_chemistry and "APTT Result Unit" in line:
            break

        # Capture chemistry information
        if capturing_chemistry and line.strip() != "":
            chemistry_info.append(line.strip())

    # If chemistry information is found, return it
    if chemistry_info:
        return chemistry_info
    else:
        print("Chemistry Information not found in the file.")
        return None


def store_info_to_csv_for_CRP(extracted_info,csv_file):
    # Write the extracted information to the CSV file
    with open(csv_file, 'w', newline='') as file:
        writer = csv.writer(file)

        # Write the column names as the header row
        writer.writerow(["Chemistry", "Unit", "Result", "Reference Range"])

        # Write the chemistry information to the CSV file
        for line in extracted_info:
            # Split each line by space and extract relevant information
            parts = line.split()
            chemistry = parts[0]
            unit = parts[1]
            result = parts[2]
            reference_range = " ".join(parts[3:])  # Concatenate extra values into the reference range
            writer.writerow([chemistry, unit, result, reference_range])


if __name__ == '__main__':
    app.run(debug=True)