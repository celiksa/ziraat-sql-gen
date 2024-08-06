from ibm_watsonx_ai import Credentials
from ibm_watsonx_ai.foundation_models import ModelInference
from ibm_watsonx_ai.metanames import GenTextParamsMetaNames as GenParams
from ibm_watsonx_ai.foundation_models.utils.enums import ModelTypes, DecodingMethods
import gradio as gr
from PIL import Image
import tempfile
import os
import http.client
import pandas as pd
import numpy as np
import json
import requests
import io
import openpyxl
#from pydantic import ValidationError
import tcmb
# Example usage with Gradio
import gradio as gr
from datetime import datetime
import random
import mimetypes
from tabulate import tabulate



#from prompt_templates import prompt_input
#from prompt_templates import prompt_input_def

import prompt_templates

prompt_input = prompt_templates.prompt_input
prompt_input_def = prompt_templates.prompt_input_def
prompt_input_sen1 = prompt_templates.prompt_input_sen1


#senaryo2_api_base_url = "http://127.0.0.1:8000/"
senaryo2_api_base_url = "https://rag-buyuk-boyutlu-dokuman-ztsqlgen.apps.6690d1a7f0f773001e2cf77c.ocp.techzone.ibm.com/"
# To display example params enter
GenParams().get_example_values()



# Model parameters
generate_params = {
    GenParams.MAX_NEW_TOKENS: 4096,
    GenParams.TEMPERATURE: 0.7,
    GenParams.TOP_P: 1,
    GenParams.TOP_K: 50,
    GenParams.REPETITION_PENALTY: 1,
    GenParams.MIN_NEW_TOKENS: 0
}

model_id = "meta-llama/llama-3-70b-instruct"
# Model inference call
model_inference = ModelInference(
    #model_id=ModelTypes.GRANITE_34B_CODE_INSTRUCT,
    model_id= model_id, #ModelTypes.LLAMA_3_70B_INSTRUCT,
    params=generate_params,
    credentials=Credentials(
                        api_key = "nbzzwhGIoF642cnM1vMMVi7ajy0IFgTICj8qJsbAh0VZ",
                        url = "https://us-south.ml.cloud.ibm.com"),
    project_id="c90bbfe9-3caf-4447-ac51-0776e1d27646"
    )


def query_db(query):

    #db2 Connection
    conn = http.client.HTTPSConnection("c3n41cmd0nqnrk39u98g.db2.cloud.ibm.com")

    payload = "{\"userid\":\"e9debea5\",\"password\":\"wKbVTQHUq7BshOt9\"}"

    DEPLOYMENT_ID= "crn:v1:bluemix:public:dashdb-for-transactions:us-south:a/98ff78eb326f477f8447f94142661697:5a45acd7-1381-4892-87a1-88495fc75b2b::"

    headers = {
        'content-type': "application/json",
        'x-deployment-id': DEPLOYMENT_ID
        }

    conn.request("POST", "/dbapi/v4/auth/tokens", payload, headers)

    res = conn.getresponse()
    data = res.read()

    response_json = json.loads(data.decode("utf-8"))
    TOKEN = response_json.get("token")

    query_headers = {
        'content-type': "application/json",
        'authorization': "Bearer " + TOKEN,
        'x-deployment-id': DEPLOYMENT_ID
        }
    print(data.decode("utf-8"))
    print(TOKEN)

    # Use the token to send a query request
    query_payload = "{\"commands\":\""+ query + "\",\"limit\":100,\"separator\":\";\",\"stop_on_error\":\"no\",\"current_schema\":\"POC_ZIRAAT\"}"
    
    
    #query_payload = "{\"commands\":\""+ query + "\",\"limit\":10,\"separator\":\";\",\"stop_on_error\":\"no\",\"current_schema\":\"POC_ZIRAAT\"}"
    query_payload = query_payload.encode('utf-8')
    

    print (query_payload)

    conn.request("POST", "/dbapi/v4/sql_jobs", query_payload, query_headers)
    res = conn.getresponse()
    data = res.read()
    print ("data: ", data)
    #print(data.decode("utf-8"))
    response_json = json.loads(data.decode("utf-8"))
    JOB_ID = response_json.get("id")
    

    conn.request("GET", f"/dbapi/v4/sql_jobs/{JOB_ID}", headers=query_headers)

    res_query = conn.getresponse()
    data = res_query.read()
    print (data)
    results_json = json.loads(data.decode("utf-8"))

    #print (results_json)
    # Extract the relevant information
    columns = results_json['results'][0]['columns']
    rows = results_json['results'][0]['rows']

    df = pd.DataFrame(rows, columns=columns)
    return df


def generate_sql(question,query_type):
    # This function takes a question and generates an SQL code snippet.
    # For the sake of this example, let's return a static SQL query.
    
    print (model_inference.model_id)
    if query_type=="SQL Açıklamalı":
        input = prompt_input_def.format(question)
    else:
        input = prompt_input.format(question)
    
    sql_query =  model_inference.generate_text(prompt=input,guardrails=False)
    
    #sql_query =  model_inference.generate(prompt=input,params=generate_params, guardrails=False)


    if query_type=="SQL":
        return sql_query, None
    elif query_type=="SQL Çalıştır":
        query_response = query_db(sql_query)     
        print(query_response) 
        return sql_query, query_response
        
    else:
        return sql_query, None
   
   # return sql_query

def change_model(model_type):
    model_inference.model_id = model_type
    print (model_inference.model_id)
    return  None


def run_query (sql_query):
    if sql_query==None or sql_query=="":
        return None
    else:
      query_response = query_db(sql_query)    
      return query_response

def add_dataframe ( query_type):
    if query_type=="SQL":
        return gr.DataFrame(visible=True,value=None), gr.Code(language="sql", value=None), gr.Button(visible=True)
    elif query_type=="SQL Açıklamalı":
        return gr.DataFrame(visible=False,value=None), gr.Code(language="sql",value=None),gr.Button(visible=False)
    else:
        return gr.DataFrame(visible=True,value=None), gr.Code(language="sql",value=None),gr.Button(visible=True)

# Function to classify a single text
def classify_text(text):
    # Replace this with your actual API call
    api_url = "https://ztclassification3-ztclassification.apps.6690d1a7f0f773001e2cf77c.ocp.techzone.ibm.com"
    
    response = requests.post(api_url, json={"text": text})
    result = response.json()
    return pd.DataFrame([{"Text": text, "Label": result["label"], "Score": result["score"]}])

# Function to classify texts from an Excel file
def classify_file(file):
    df = pd.read_excel(file.name, header=None)
    results = []
    for text in df.iloc[:, 0]:
        result = classify_text(text).iloc[0]
        results.append(result)
    return pd.DataFrame(results)

def send_to_chatbot(file):
    df = pd.read_excel(file.name, header=None)
    results = []
    inputs = []
    for text in df.iloc[:, 0]:
        inputs.append(text)
        input = prompt_input_sen1.format(text)
        print (input)
        result =  model_inference.generate_text(prompt=input,guardrails=False)
        print (result)
        results.append(result)
    result_df = pd.DataFrame({
          'Soru': inputs,
          'Asistan Cevap': results
      })
    return result_df

# Function to save results to Excel
def save_to_excel(df):
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False)
    output.seek(0)

       # Save the BytesIO content to a temporary file
    temp_file = tempfile.NamedTemporaryFile(delete=False, prefix="ziraat_output_",suffix='.xlsx')
    temp_file.write(output.read())
    temp_file.close()

    return temp_file.name

def sql_result_to_table_string(result):
    if isinstance(result, pd.DataFrame):
        if result.empty:
            return "Query returned an empty DataFrame."
        return tabulate(result, headers='keys', tablefmt='pretty', showindex=False)
    elif isinstance(result, list):
        if not result:
            return "No results found."
        df = pd.DataFrame(result[1:], columns=result[0])
        return tabulate(df, headers='keys', tablefmt='pretty', showindex=False)
    else:
        return str(result)  # Fallback for unexpected result types
    

def sql_file (file, query_type):
      
      df = pd.read_excel(file.name, header=None)
      input_texts = []
      generated_sqls = []
      sql_results=[]
      
      for text in df.iloc[:, 0]:
          
          input_texts.append(text)
          
          if query_type == "SQL Açıklamalı":
              input = prompt_input_def.format(text)

          else:
              input = prompt_input.format(text)

              
          
          sql_query = model_inference.generate_text(prompt=input, guardrails=False)
      
            
          if query_type =="SQL":
              try:
                result = query_db(sql_query)
                if result is not None:
                    table_string = sql_result_to_table_string(result)
                    sql_results.append(table_string)
                else:
                        sql_results.append("Query returned no results or encountered an error.")
              except Exception as e:
                    error_message = f"An error occurred while executing the query: {e}"
                    print(error_message)
                    sql_results.append(error_message)
          else:
              sql_results.append("")
              
          

          print(sql_query)
          generated_sqls.append(sql_query)
      print (input_texts)
      print(generated_sqls)
      # Create DataFrame with two columns
      result_df = pd.DataFrame({
          'Soru': input_texts,
          'SQL Kodu': generated_sqls,
          'Veri Sonuç': sql_results
      })
      
      print(result_df)
    
      
      return result_df

def send_to_tcmb(input,type):
    
    api_key = os.environ.get('OPENAI_API_KEY')

    
    try:
        response = tcmb.index(input, api_key)
    
        print (response)
        # Extract the generated_answer
        generated_answer = response['generated_answer']

        # Remove the generated_answer from the original dictionary
        rest_of_data = response.copy()
        del rest_of_data['generated_answer']

        # Convert the rest of the data to a string
        rest_of_data_str = str(rest_of_data)
        if type == "normal":
            return generated_answer, rest_of_data_str
        # Create a DataFrame
        else:
            df = pd.DataFrame({
                'Cevap': [generated_answer],
                'JSON Detay': [rest_of_data_str]
            })
            return  df
    except Exception as e:
        # Handle the exception
        if response:
            error_message = response
        else:
            error_message = "Servisten Cevap Alınamadı"
        # You might want to log the error or return it to the user
        return error_message, error_message

def tcmb_file (file):
      
      df = pd.read_excel(file.name, header=None)
      input_texts = []
      generated_text = []
      generated_json=[]
      
      for text in df.iloc[:, 0]:
          
          input_texts.append(text)
          
          tcmb_text, tcmb_json = send_to_tcmb(text, "normal")

          #print(sql_query)
          generated_text.append(tcmb_text)
          generated_json.append(tcmb_json)
      #print (input_texts)
      #print(generated_sqls)
      # Create DataFrame with two columns
      result_df = pd.DataFrame({
          'Soru': input_texts,
          'Cevap': generated_text,
          'JSON Detay': generated_json
      })
      
      #print(result_df)
    
      
      return result_df

#Senaryo 2 add files
def get_mime_type(file_extension):
    mime_types = {
        '.xlsx': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        '.xls': 'application/vnd.ms-excel',
        '.pdf': 'application/pdf',
        '.docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
        '.doc': 'application/msword',
        '.txt': 'text/plain'
    }
    return mime_types.get(file_extension.lower(), mimetypes.guess_type(file_extension)[0] or 'application/octet-stream')

def upload_pdf(files, collection_name):
    url = senaryo2_api_base_url + "upload_pdfs"
    # Prepare the files dictionary
    file_type = os.path.splitext(files)[1].lower()
    mime_type = get_mime_type(file_type)

    file = {'files': (files, open(files, 'rb'), mime_type)}
    
    # Prepare the parameters
    params = {'collection_name': collection_name}
    
    # Set the headers
    headers = {'accept': 'application/json'}
    
    try:
        # Make the POST request
        response = requests.post(url, params=params, headers=headers, files=file)
        
        json_response = response.json()
        
        # Extract and return the collection_name from the response
        return json_response.get('collection_name')
    except requests.exceptions.RequestException as e:
        print(f"An error occurred: {e}")
        return None
    #finally:
        # Ensure the file is closed
        #files['files'][1].close()

def add_files_to_collection(files):
    
    #print (file_types)
    if not files:
        return "No files selected."
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    random_suffix = ''.join(random.choices('abcdefghijklmnopqrstuvwxyz0123456789', k=6))
    collection_name = f"collection_{timestamp}_{random_suffix}"
    result = None
    for file in files:
        result = upload_pdf(file,collection_name)
    return result

def send_to_rag(query,collection_name, max_token=900):
    url = senaryo2_api_base_url + "perform_rag"
    # Prepare the headers
    headers = {
        'accept': 'application/json',
        'Content-Type': 'application/json'
    }

    # Prepare the payload
    payload = {
        "collection_name": collection_name,
        "query": query,
        "max_token": max_token
    }

    try:
        # Make the POST request
        response = requests.post(url, headers=headers, data=json.dumps(payload))
        
        # Check if the request was successful
        response.raise_for_status()
        
        # Parse the JSON response
        json_response = response.json()
        
        # Extract and return only the 'result' field
        return json_response.get('result')
    except requests.exceptions.RequestException as e:
        print(f"An error occurred: {e}")
        return None

def file_to_RAG(file,collection_name, max_token = 900):
    df = pd.read_excel(file.name, header=None)
    results = []
    inputs = []
    for text in df.iloc[:, 0]:
        inputs.append(text)
        
        result =  send_to_rag(text,collection_name, max_token)
        #print (result)
        results.append(result)
    result_df = pd.DataFrame({
          'Soru': inputs,
          'RAG Cevap': results
      })
    return result_df

def send_to_bigdoc(query, max_token=900):
    url = senaryo2_api_base_url + "perform_big_rag"
    # Prepare the headers
    headers = {
        'accept': 'application/json',
        'Content-Type': 'application/json'
    }

    # Prepare the payload
    payload = {
        "query": query,
        "max_token": max_token
    }

    try:
        # Make the POST request
        response = requests.post(url, headers=headers, data=json.dumps(payload))
        
        # Check if the request was successful
        response.raise_for_status()
        
        # Parse the JSON response
        json_response = response.json()
        
        # Extract and return only the 'result' field
        return json_response.get('result')
    except requests.exceptions.RequestException as e:
        print(f"An error occurred: {e}")
        return None

def file_to_bigdoc(file, max_token = 900):
    df = pd.read_excel(file.name, header=None)
    results = []
    inputs = []
    for text in df.iloc[:, 0]:
        inputs.append(text)
        
        result =  send_to_bigdoc(text, max_token)
        #print (result)
        results.append(result)
    result_df = pd.DataFrame({
          'Soru': inputs,
          'Big Doc Cevap': results
      })
    return result_df

def send_to_excel(query, max_token=900):
    url = senaryo2_api_base_url + "perform_excel_rag"
    # Prepare the headers
    headers = {
        'accept': 'application/json',
        'Content-Type': 'application/json'
    }

    # Prepare the payload
    payload = {
        "query": query,
        "max_token": max_token
    }

    try:
        # Make the POST request
        response = requests.post(url, headers=headers, data=json.dumps(payload))
        
        # Check if the request was successful
        response.raise_for_status()
        
        # Parse the JSON response
        json_response = response.json()
        
        # Extract and return only the 'result' field
        return json_response.get('result')
    except requests.exceptions.RequestException as e:
        print(f"An error occurred: {e}")
        return None

def file_to_excel(file, max_token = 900):
    df = pd.read_excel(file.name, header=None)
    results = []
    inputs = []
    for text in df.iloc[:, 0]:
        inputs.append(text)
        
        result =  send_to_excel(text, max_token)
        #print (result)
        results.append(result)
    result_df = pd.DataFrame({
          'Soru': inputs,
          'Excel Cevap': results
      })
    return result_df


def send_to_tablo(query, max_token=900):
    url = senaryo2_api_base_url + "perform_table_rag"
    # Prepare the headers
    headers = {
        'accept': 'application/json',
        'Content-Type': 'application/json'
    }

    # Prepare the payload
    payload = {
        "query": query,
        "max_token": max_token
    }

    try:
        # Make the POST request
        response = requests.post(url, headers=headers, data=json.dumps(payload))
        
        # Check if the request was successful
        response.raise_for_status()
        
        # Parse the JSON response
        json_response = response.json()
        
        # Extract and return only the 'result' field
        return json_response.get('result')
    except requests.exceptions.RequestException as e:
        print(f"An error occurred: {e}")
        return None

def file_to_tablo(file, max_token = 900):
    df = pd.read_excel(file.name, header=None)
    results = []
    inputs = []
    for text in df.iloc[:, 0]:
        inputs.append(text)
        
        result =  send_to_tablo(text, max_token)
        #print (result)
        results.append(result)
    result_df = pd.DataFrame({
          'Soru': inputs,
          'Tablo Cevap': results
      })
    return result_df


iframe_url = "https://web-chat.global.assistant.watson.appdomain.cloud/preview.html?backgroundImageURL=https%3A%2F%2Feu-de.assistant.watson.cloud.ibm.com%2Fpublic%2Fimages%2Fupx-b6be7111-313a-4ea9-81d0-e191261e9f66%3A%3A12d2f1fc-dbcf-4df1-a091-ab6933b57c0a&integrationID=b483e10c-006f-4743-a2d8-7a24ede095a6&region=eu-de&serviceInstanceID=b6be7111-313a-4ea9-81d0-e191261e9f66"
#iframe_url = iframe_url.encode("utf-8")
html_code = f"""
<iframe src="{iframe_url}" style="width:100%; height:500px; border:none;"></iframe>
"""

iframe_url_sen1 = "https://web-chat.global.assistant.watson.appdomain.cloud/preview.html?backgroundImageURL=https%3A%2F%2Fus-south.assistant.watson.cloud.ibm.com%2Fpublic%2Fimages%2Fupx-da966e02-efb8-4ac7-a59c-c64cd30d7628%3A%3A1273bc22-77cd-40fb-9b08-841fd28797b3&integrationID=d7abeb57-baf9-41c0-b53e-663500b50a70&region=us-south&serviceInstanceID=da966e02-efb8-4ac7-a59c-c64cd30d7628"
#iframe_url = iframe_url.encode("utf-8")
html_code_sen1 = f"""
<iframe src="{iframe_url_sen1}" style="width:100%; height:500px; border:none;"></iframe>
"""

# Define the path to your guide image
#image_path = "guest-template.png"  # Replace with your image path
image_path = "images/Ziraat_POC_S4_ER.png"  # Replace with your image path

#image_path_ziraat = "images/ziraat_logo.png"
image_path_ziraat = "images/ibm.png"
image_path_ibm = "images/ibm.png"

img = Image.open(image_path)
img_ziraat = Image.open(image_path_ziraat)
img_ibm = Image.open(image_path_ibm)



html_img1 = """
<div style="display: flex; align-items: center;">
  <img src="https://logos-world.net/wp-content/uploads/2021/02/Ziraat-Bankasi-Logo.png" style="width: 20%; height: auto; margin-right: 50px;">
  <div style="text-align: justify;"><h1>ÜRETKEN YAPAY ZEKA BÜYÜK DİL MODELLERİ KAVRAM KANITI (POC)</div>
</div>

"""

js_func = """
function refresh() {
    const url = new URL(window.location);

    if (url.searchParams.get('__theme') !== 'light') {
        url.searchParams.set('__theme', 'light');
        window.location.href = url.href;
    }
}
"""

theme = gr.themes.Base().set(
    button_primary_background_fill='red',
    button_primary_text_color='white'
)

html_widget = gr.HTML(html_code)
html_widget_sen1 = gr.HTML(html_code_sen1)

with gr.Blocks(js=js_func,theme=theme) as demo:
    
    with gr.Row():  
        image_html1 = gr.HTML(html_img1)

    
    with gr.Tab("Senaryo 4 - DB Entegrasyonu"):
        with gr.Accordion("Tekli Sorgu", open=False):
          with gr.Row():
            text_output = gr.Code(label="SQL Kodu", language="sql", interactive=True)
            
            with gr.Column():
              text_result = gr.DataFrame(label="SQL Sorgu Sonuç",interactive=False, visible=True)  
              run_button = gr.Button("Çalıştır", visible=True)
          with gr.Row():
            text_input = gr.Textbox(lines=2, label="Soru", scale=3)
            with gr.Column():              
              query_type = gr.Dropdown(choices=["SQL", "SQL Açıklamalı"], label="Sorgu Tipi Seçiniz", scale=1, value="SQL",interactive=True)
              #model_type = gr.Dropdown(choices=["meta-llama/llama-3-70b-instruct", "meta-llama/llama-3-405b-instruct","ibm/granite-34b-code-instruct"], label="Model Seçiniz", scale=1, value="meta-llama/llama-3-70b-instruct",interactive=True)
          with gr.Row():  
            text_button = gr.Button("Gönder", variant="primary")
            clear_butoon = gr.ClearButton(components=[text_input,text_output, text_result],value="Temizle", variant="stop" )
        
          examples = gr.Examples(
              examples=[
                    "Bireysl seggmentte kaç müşteri vardır?",
                    "Açık şubeler arasında ATM sayısı en az olan hangisidir?",
                    "Kurumsal&Ticari müşterilerin  en az sahip olduğu ürün nedir?",
                    "Açık şubeler arasında en fazla müşterisi olan şube hangisidir, \"GM HAVUZU\" hariç"], 
                    inputs=text_input,label="Örnek sorgular")
          """examples = gr.Examples(
              examples=[
                    "Geçtiğimiz altı ay içinde en fazla gelir getiren en iyi 5 ürünü bul",
                    "En fazla net toplam puan kazanan ve toplam bilet sayısına sahip en iyi 5 müşteriyi bul",
                    "En çok yorumu olan müşteriler kimler?"], 
                    inputs=text_input,label="Örnek sorgular")"""
          
          """  examples = gr.Examples(
              examples=[
                    "Find the top 5 products that have generated the most revenue in the past six months",
                    "find the top 5 customers who earned largest net total points with total number of tickets ",
                    "What customers has most reviews"], 
                    inputs=text_input,label="Örnek sorgular") """
          text_button.click(fn=generate_sql, inputs=[text_input,query_type], outputs=[text_output,text_result])
          query_type.change(fn=add_dataframe, inputs=query_type, outputs=[text_result,text_output, run_button])
          #model_type.change(fn=change_model, inputs=model_type)
          run_button.click(fn=run_query, inputs=text_output, outputs=text_result )
        with gr.Accordion("Çoklu Sorgu", open=False):
            with gr.Row():
                with gr.Column():
                  file_db_input = gr.File(label="Excel Dosyası Ekle", file_types=[".xlsx"])
                  query_db_type = gr.Dropdown(choices=["SQL", "SQL Açıklamalı"], label="Sorgu Tipi Seçiniz", scale=1, value="SQL",interactive=True)
                file_db_output = gr.DataFrame(label="SQL Kodları", interactive=False, scale=3,wrap=True)
            with gr.Row():
                file_db_button = gr.Button("Dosyadan SQL Kodları Oluştur", variant="primary")
                file_clear_db_button = gr.ClearButton(components=[file_db_input, file_db_output], value="Temizle", variant="stop")
            with gr.Row():
                download_db_button = gr.Button("Sonuçları İndir")
            

            file_db_button.click(fn=sql_file, inputs=[file_db_input,query_db_type], outputs=file_db_output)
            download_db_button.click(fn=save_to_excel, inputs=file_db_output, outputs=gr.File())
        with gr.Accordion("DB Şeması İçin Tıklayınız!", open=False):
     
          """ sql_type = gr.Dropdown(
                    ["SQL", "PL/SQL"], label="SQL Tipi"
          ), """
          guide_image = gr.Image(type="pil", value=img, label="Kullanılan DB Şeması")


    with gr.Tab("Senaryo 5 - Kategori Tespiti "):  
      with gr.Accordion("Watsonx Assistant", open=False):
          with gr.Row():
                html_widget.render()
      with gr.Accordion("Tekli Sorgu", open=False):
        with gr.Row():
          class_input = gr.Textbox(lines=2, label="Tekli Sorgu", scale=2, interactive=True)
          class_output = gr.DataFrame(label="Sınıflandırma Sonucu",interactive=False, visible=True,scale=3,wrap=True)
        with gr.Row():  
            class_button = gr.Button("Sınıflandır", variant="primary")
            class_clear_butoon = gr.ClearButton(components=[class_input,class_output],value="Temizle", variant="stop" )
        examples_class = gr.Examples(
             examples=[
                  "İtiraz Nedeni: #### Açıklama:  ORGANIZATION Hizmet Detayı:  ORGANIZATION Hizmet Tarihi: 01.01.1900 00:00:00 ORGANIZATION Hizmet Açıklaması:  Harcama İtirazı"],
                  inputs=class_input,label="Örnek sorgular")

        class_button.click(fn=classify_text, inputs=class_input, outputs=class_output)

      with gr.Accordion("Çoklu Sorgu", open=False):
            with gr.Row():
                file_input = gr.File(label="Excel Dosyası Ekle", file_types=[".xlsx"])
                file_output = gr.DataFrame(label="Sınıflandırma Sonuçları", interactive=False, scale=3,wrap=True)
            with gr.Row():
                file_button = gr.Button("Dosyayı Sınıflandır", variant="primary")
                file_clear_button = gr.ClearButton(components=[file_input, file_output], value="Temizle", variant="stop")
            with gr.Row():
                download_button = gr.Button("Sonuçları İndir")
            

            file_button.click(fn=classify_file, inputs=file_input, outputs=file_output)
            download_button.click(fn=save_to_excel, inputs=file_output, outputs=gr.File())

    with gr.Tab("Senaryo 1 - Genel Sohbet Botu"):
        with gr.Accordion("Watsonx Assistant", open=False):
          with gr.Row():
                html_widget_sen1.render()
        with gr.Accordion("Çoklu Sorgu", open=False):
            with gr.Row():
                file_input_sen1 = gr.File(label="Excel Dosyası Ekle", file_types=[".xlsx"])
                file_output_sen1 = gr.DataFrame(label="Chatbot Sonuçları", interactive=False, scale=3,wrap=True)
            with gr.Row():
                file_button_sen1 = gr.Button("Dosyayı Chatbota Gönder", variant="primary")
                file_clear_button_sen1 = gr.ClearButton(components=[file_input_sen1, file_output_sen1], value="Temizle", variant="stop")
            with gr.Row():
                download_button_sen1 = gr.Button("Sonuçları İndir")
            

            file_button_sen1.click(fn=send_to_chatbot, inputs=file_input_sen1, outputs=file_output_sen1)
            download_button_sen1.click(fn=save_to_excel, inputs=file_output_sen1, outputs=gr.File())

    with gr.Tab("Senaryo 3 - Servis Entegrasyonu", interactive=False):
        with gr.Accordion("Tekli Sorgu", open=False):
            with gr.Row():
                    with gr.Column(scale=1):
                        text_3_output = gr.Textbox(interactive=False, label="Cevap")
                    with gr.Column(2):
                        text_3_output_json = gr.Textbox(interactive=False,label="JSON Detay")
            with gr.Row():
                        text_3_input = gr.Textbox(lines=2, label="Soru")

            with gr.Row():
                    button_sen_3 = gr.Button("Gönder", variant="primary")
                    clear_button_sen3 = gr.ClearButton(components=[text_3_input, text_3_output], value="Temizle", variant="stop")
            examples_3 = gr.Examples(
                examples=[
                        "Nisan 2024'te İsviçre Frangı'nın Türk Lirası karşısında gördüğü en yüksek seviye nedir?",
                        "Merkez Bankası'nın açıkladığı son verilere göre Yurt Dışında Yerleşik Kişilerin Portföyündeki Hisse Senedi ve Borçlanma Senetlerinin yıllık değişim oranı nedir?",
                        "2023 yılında toplam Banka Kartı ve Kredi Kartı harcamalarının yüzde kaçı Havayolları ve Konaklama sektörlerinde yapılmıştır? Harcama tutarlarıyla beraber göster."],
                        inputs=text_3_input,label="Örnek sorgular")
            button_sen_3.click(
                fn=lambda x: send_to_tcmb(x, "normal"),
                inputs=[text_3_input],
                outputs=[text_3_output, text_3_output_json]
            )
        

        with gr.Accordion("Çoklu Sorgu", open=False):
            with gr.Row():
                    file_input_sen3 = gr.File(label="Excel Dosyası Ekle", file_types=[".xlsx"],scale=1)
                    file_output_sen3 = gr.DataFrame(label="Sorgu Sonuçları", interactive=False,wrap=True, col_count=3,scale=3)
            with gr.Row():
                    file_button_sen3 = gr.Button("Dosyayı Servise Gönder", variant="primary")
                    file_clear_button_sen3 = gr.ClearButton(components=[file_input_sen3, file_output_sen3], value="Temizle", variant="stop")
            with gr.Row():
                    download_button_sen3 = gr.Button("Sonuçları İndir")
            
            
            file_button_sen3.click(fn=tcmb_file, inputs=file_input_sen3, outputs=file_output_sen3)
            download_button_sen3.click(fn=save_to_excel, inputs=file_output_sen3, outputs=gr.File())

  
    with gr.Tab("Senaryo 2 - Doküman Bazlı Cevaplama", interactive=False):
        with gr.Row():
            max_token = gr.Text("400", interactive=True, scale=1, label="Max Token")
        with gr.Tab("RAG Genel"):
           
            with gr.Row():
                with gr.Column(scale=1):
                     file_input_sen21 = gr.File(label="Excel Dosyası Ekle", file_types=[".xlsx",".pdf",".docx","doc",".txt",".xls"],interactive=True, file_count="multiple")
                with gr.Column(scale=2):
                    file_button_sen21 = gr.Button("Dosyaları Gönder", variant="primary")
                    file_clear_button_sen21 = gr.ClearButton(components=[file_input_sen21, file_output_sen3], value="Temizle", variant="stop")
                    file_output_sen21 = gr.Textbox(label="Collection", interactive=False)

                file_button_sen21.click(fn=add_files_to_collection, inputs=[file_input_sen21], outputs=file_output_sen21)
            
            with gr.Accordion("Tekli Sorgu", open=False):
                with gr.Row():
                    sen21_input = gr.Textbox(lines=2, label="Soru", scale=1, interactive=True)
                    sen21_output = gr.Textbox(label="Cevap",interactive=False,scale=2)
                with gr.Row():  
                    sen21_button = gr.Button("Soruyu Gönder", variant="primary")
                    sen21_clear_butoon = gr.ClearButton(components=[sen21_input,sen21_output],value="Temizle", variant="stop" )

                sen21_button.click(fn=send_to_rag, inputs=[sen21_input,file_output_sen21,max_token], outputs=sen21_output)
    
            with gr.Accordion("Çoklu Sorgu", open=False):
                with gr.Row():
                    file_input_sen211 = gr.File(label="Excel Dosyası Ekle", file_types=[".xlsx"])
                    file_output_sen211 = gr.DataFrame(label="RAG Sonuçları", interactive=False, scale=3,wrap=True, col_count=2)
                with gr.Row():
                    file_button_sen211 = gr.Button("Dosyayı Gönder", variant="primary")
                    file_clear_button_sen211 = gr.ClearButton(components=[file_input_sen211, file_output_sen211], value="Temizle", variant="stop")
                with gr.Row():
                    download_button_sen211 = gr.Button("Sonuçları İndir")
                

                file_button_sen211.click(fn=file_to_RAG, inputs=[file_input_sen211,file_output_sen21,max_token], outputs=file_output_sen211)
                download_button_sen211.click(fn=save_to_excel, inputs=file_output_sen211, outputs=gr.File())
        
        with gr.Tab("Büyül Boyutlu Dosya"):
           
            
            with gr.Accordion("Tekli Sorgu", open=False):
                with gr.Row():
                    sen22_input = gr.Textbox(lines=2, label="Soru", scale=1, interactive=True)
                    sen22_output = gr.Textbox(label="Cevap",interactive=False,scale=2)
                with gr.Row():  
                    sen22_button = gr.Button("Soruyu Gönder", variant="primary")
                    sen22_clear_butoon = gr.ClearButton(components=[sen22_input,sen22_output],value="Temizle", variant="stop" )

                sen22_button.click(fn=send_to_bigdoc, inputs=[sen22_input, max_token], outputs=sen22_output)
    
            with gr.Accordion("Çoklu Sorgu", open=False):
                with gr.Row():
                    file_input_sen22 = gr.File(label="Excel Dosyası Ekle", file_types=[".xlsx"])
                    file_output_sen22 = gr.DataFrame(label="Büyü Boyutlu Döküman Sonuçları", interactive=False, scale=3,wrap=True, col_count=2)
                with gr.Row():
                    file_button_sen22 = gr.Button("Dosyayı Gönder", variant="primary")
                    file_clear_button_sen22 = gr.ClearButton(components=[file_input_sen22, file_output_sen22], value="Temizle", variant="stop")
                with gr.Row():
                    download_button_sen22 = gr.Button("Sonuçları İndir")
                

                file_button_sen22.click(fn=send_to_bigdoc, inputs=[file_input_sen22,max_token], outputs=file_output_sen22)
                download_button_sen22.click(fn=save_to_excel, inputs=file_output_sen22, outputs=gr.File())

        with gr.Tab("Excel"):
  
            with gr.Accordion("Tekli Sorgu", open=False):
                with gr.Row():
                    sen23_input = gr.Textbox(lines=2, label="Soru", scale=1, interactive=True)
                    sen23_output = gr.Textbox(label="Cevap",interactive=False,scale=2)
                with gr.Row():  
                    sen23_button = gr.Button("Soruyu Gönder", variant="primary")
                    sen23_clear_butoon = gr.ClearButton(components=[sen23_input,sen23_output],value="Temizle", variant="stop" )

                sen23_button.click(fn=send_to_excel, inputs=[sen23_input, max_token], outputs=sen23_output)
    
            with gr.Accordion("Çoklu Sorgu", open=False):
                with gr.Row():
                    file_input_sen23 = gr.File(label="Excel Dosyası Ekle", file_types=[".xlsx"])
                    file_output_sen23 = gr.DataFrame(label="Excel Sonuçları", interactive=False, scale=3,wrap=True)
                with gr.Row():
                    file_button_sen23 = gr.Button("Dosyayı Gönder", variant="primary")
                    file_clear_button_sen23 = gr.ClearButton(components=[file_input_sen23, file_output_sen23], value="Temizle", variant="stop")
                with gr.Row():
                    download_button_sen23 = gr.Button("Sonuçları İndir")
                

                file_button_sen23.click(fn=file_to_excel, inputs=[file_input_sen23,max_token], outputs=file_output_sen23)
                download_button_sen23.click(fn=save_to_excel, inputs=file_output_sen23, outputs=gr.File())

        with gr.Tab("Tablo Sorgu"):
  
            with gr.Accordion("Tekli Sorgu", open=False):
                with gr.Row():
                    sen24_input = gr.Textbox(lines=2, label="Soru", scale=1, interactive=True)
                    sen24_output = gr.Textbox(label="Cevap",interactive=False,scale=2)
                with gr.Row():  
                    sen24_button = gr.Button("Soruyu Gönder", variant="primary")
                    sen24_clear_butoon = gr.ClearButton(components=[sen24_input,sen24_output],value="Temizle", variant="stop" )

                sen24_button.click(fn=send_to_tablo, inputs=[sen24_input, max_token], outputs=sen24_output)
    
            with gr.Accordion("Çoklu Sorgu", open=False):
                with gr.Row():
                    file_input_sen24 = gr.File(label="Excel Dosyası Ekle", file_types=[".xlsx"])
                    file_output_sen24 = gr.DataFrame(label="Tablo Sorgu Sonuçları", interactive=False, scale=3,wrap=True)
                with gr.Row():
                    file_button_sen24 = gr.Button("Dosyayı Gönder", variant="primary")
                    file_clear_button_sen24 = gr.ClearButton(components=[file_input_sen24, file_output_sen24], value="Temizle", variant="stop")
                with gr.Row():
                    download_button_sen24 = gr.Button("Sonuçları İndir")
                

                file_button_sen24.click(fn=file_to_tablo, inputs=[file_input_sen24,max_token], outputs=file_output_sen24)
                download_button_sen24.click(fn=save_to_excel, inputs=file_output_sen24, outputs=gr.File())

            
            
            
                

            
                        
              
          #with gr.Tab("Revize Döküman"):
              
          #with gr.Tab("URL"):
              
          #with gr.Tab("Büyük Boy"):
          
          #with gr.Row():
              # text_2 = gr.Textbox()


demo.launch( server_name="0.0.0.0", server_port=7860)

