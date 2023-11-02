import streamlit as st
import pandas as pd
import numpy as np
import gensim
from gensim.models import KeyedVectors
import re
import string
import nltk
from nltk.corpus import stopwords
from nltk.stem import WordNetLemmatizer
from nltk.tokenize import word_tokenize
import joblib
import requests

# URL of the large binary file hosted on an external service
file_url = 'https://huggingface.co/NathaNn1111/word2vec-google-news-negative-300-bin/resolve/main/GoogleNews-vectors-negative300.bin'

# Destination path where the file will be saved locally
local_path = 'GoogleNews-vectors-negative300.bin'

# Download the file
response = requests.get(file_url)
with open(local_path, 'wb') as file:
    file.write(response.content)

print('File downloaded successfully.')


# Load SVM model and Word2Vec model
model = joblib.load('svm_model.pkl')
embedding_model = KeyedVectors.load_word2vec_format('GoogleNews-vectors-negative300.bin', binary=True)

# Download necessary NLTK datasets
nltk.download('punkt')
nltk.download('wordnet')
nltk.download('stopwords')
nltk.download('omw-1.4')


#Data Processing
def preprocessing_policy(policy):
    stop_words = set(stopwords.words('english'))
    lemmatizer = WordNetLemmatizer()
   
    policy = policy.lower()
    policy = re.sub('[%s]' % re.escape(string.punctuation), '', policy)
    policy = re.sub('\w*\d\w*', '', policy)
    tokens = word_tokenize(policy)
    tokens = [lemmatizer.lemmatize(word) for word in tokens if word not in stop_words]
    return tokens


#Feature Extraction - Google News Word2Vec Model
def feature_extraction(df):
    #Load Google News Word2Vec Model
    
    w2v_data = get_word2vec_embeddings(embedding_model, df)
    return w2v_data


#Create Vector Representations for Policies
def get_average_word2vec(preprocessed_datapoint, w2v_model, generate_missing=False, k=300):
    if len(preprocessed_datapoint)<1:
        return np.zeros(k)
    
    # Assign vector value if token is not in model: depends on generate_missing, = 0 in this case
    if generate_missing:
        vectorized = [w2v_model[token] if token in w2v_model else np.random.rand(k) for token in preprocessed_datapoint]
    else:
        vectorized = [w2v_model[token] if token in w2v_model else np.zeros(k) for token in preprocessed_datapoint]
    
    # Calculate the average vector of the datapoint 
    # by dividing sum of values in same axis to the number of token in a datapoint
    length_datapoint = len(vectorized)
    summed_vector = np.sum(vectorized, axis=0)
    averaged_vector = np.divide(summed_vector, length_datapoint)

    return averaged_vector

def get_word2vec_embeddings(model, data, generate_missing=False):
    embeddings = data['tokens'].apply(lambda x: get_average_word2vec(x, model, generate_missing=generate_missing))
    print("Done word embedded")
    return list(embeddings)


#Text input classification
def classify_policy(policy_text):
    # Preprocess the policy
    tokens = preprocessing_policy(policy_text)
    df_tokens = pd.DataFrame({'tokens': [tokens]})
    embedding = feature_extraction(df_tokens)
    # Predict using SVM
    embedding_array = np.array(embedding)
    svm_prediction = model.predict(embedding_array.reshape(1, -1))[0]
    return svm_prediction

#Split policies to classify each policy
def split_into_paragraphs(document_content):
    # Normalize the line breaks
    normalized_content = document_content.replace('\r\n', '\n')
    # Split the document by double line breaks
    chunks = [p.strip() for p in normalized_content.split('\n\n') if p.strip()]
    
    paragraphs = []
    current_para = ""
    for chunk in chunks:
        # If the chunk starts with any list indicator, append it to the current paragraph
        if chunk.startswith(('•', '+', '-')):
            current_para += '\n' + chunk
        else:
            # If we have content in the current paragraph, store it and start a new one
            if current_para:
                paragraphs.append(current_para)
                current_para = ""
            current_para = chunk
    # Add any remaining content to the paragraphs list
    if current_para:
        paragraphs.append(current_para)
    return paragraphs


#Highlight problems
def highlight_problems(text, problem_list):
    for problem in problem_list:
        # Replace newlines with spaces and then escape the entire string
        escaped_problem = re.escape(problem.replace('\n', ' '))
        # Create a regex pattern that accounts for variable whitespace
        pattern = escaped_problem.replace(r'\ ', r'\s+')
        highlighted = f'<span style="background-color: #ff0000;">{problem}</span>'
        text = re.sub(pattern, highlighted, text)
    return text.replace('\n', '<br>')


def main():
    st.title('Privacy Policy Validator')

    # Create a text area widget for user input
    text = st.text_area('Enter Text', '')

    # Create a button to trigger validation
    if st.button('Validate'):
        # Validation logic
        problem_list = []
        paragraphs = split_into_paragraphs(text)

        for paragraph in paragraphs:
            prediction = classify_policy(paragraph)
            if prediction == 0:
                problem_list.append(paragraph)

        if len(problem_list) >= 1:
            text = highlight_problems(text, problem_list)

        # Display results
        st.write("Here is the problematic part:")
        st.write(problem_list)

if __name__ == '__main__':
    main()