from django.shortcuts import render
from django.http import JsonResponse
import openai
from azure.storage.blob import BlobServiceClient
import PyPDF2
from io import BytesIO
import spacy
from spacy.lang.es.stop_words import STOP_WORDS
from string import punctuation
from collections import Counter
from heapq import nlargest

# nlp = spacy.load('es_dep_news_trf')
nlp = spacy.load("es_core_news_sm")

openai_api_key = '----KEY API OPENAI----'
openai.api_key = openai_api_key

account_name = 'blobtfm'
azure_blob_key = '----KEY API AZURE BLOB----'
container_name = 'tfms'

#create a client to interact with blob storage
connect_str = 'DefaultEndpointsProtocol=https;AccountName=' + account_name + ';AccountKey=' + azure_blob_key + ';EndpointSuffix=core.windows.net'
blob_service_client = BlobServiceClient.from_connection_string(connect_str)

def leer_pdf_desde_azure(blob_name: str) -> str:
    blob_client = blob_service_client.get_blob_client(container=container_name, blob=blob_name)
    blob_data = blob_client.download_blob()

    # Convertir el blob a BytesIO
    blob_content = BytesIO(blob_data.readall())

    # Leer PDF y convertir a texto
    pdf_reader = PyPDF2.PdfReader(blob_content)
    text = ""
    for page_num in range(len(pdf_reader.pages)):
        text += pdf_reader.pages[page_num].extract_text()

    doc = nlp(text)
    keyword = []
    stopwords = list(STOP_WORDS)
    pos_tag = ['PROPN', 'ADJ', 'NOUN', 'VERB']
    for token in doc:
        if(token.text in stopwords or token.text in punctuation):
            continue
        if(token.pos_ in pos_tag):
            keyword.append(token.text)

    freq_word = Counter(keyword)

    max_freq = Counter(keyword).most_common(1)[0][1]

    for word in freq_word.keys():  
        freq_word[word] = (freq_word[word]/max_freq)

    sent_strength={}
    for sent in doc.sents:
        for word in sent:
            if word.text in freq_word.keys():
                if sent in sent_strength.keys():
                    sent_strength[sent]+=freq_word[word.text]
                else:
                    sent_strength[sent]=freq_word[word.text]
    
    summarized_sentences = nlargest(3, sent_strength, key=sent_strength.get)

    final_sentences = [ w.text for w in summarized_sentences ]
    summary = ' '.join(final_sentences)

    return summary

def ask_openai(message):
    response = openai.Completion.create(
        model = "text-davinci-003",
        prompt = message,
        max_tokens = 150,
        n = 1,
        stop = None,
        temperature = 0.7,
    )
    answer = response.choices[0].text.strip()
    return answer

# Create your views here.
def summarizer(request):
    if request.method == 'POST':
        message = request.POST.get('message')
        if 'resumen' and 'tfm' in message:
            if 'biologia' or 'salud' in message:
                nombre_blob = "Bio y Salud/TFM_Covadonga_Gonzalez.pdf"
                response = leer_pdf_desde_azure(nombre_blob)
            if 'steam' or 'ingenieria' in message:
                nombre_blob = "STEAM/llerenaortizvaleriafernanda.pdf"
                response = leer_pdf_desde_azure(nombre_blob)
            if 'ciencias sociales' or 'comunicacion' in message:
                nombre_blob = "Socia y Comuni/TFM_EstellaLumbrerasMikel.pdf"
                response = leer_pdf_desde_azure(nombre_blob)
        else:
            response = ask_openai(message)
        return JsonResponse({'message': message, 'response': response})
    return render(request, 'summarizer.html')