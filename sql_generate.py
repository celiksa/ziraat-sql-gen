from ibm_watsonx_ai import Credentials
from ibm_watsonx_ai.foundation_models import ModelInference
from ibm_watsonx_ai.metanames import GenTextParamsMetaNames as GenParams
from ibm_watsonx_ai.foundation_models.utils.enums import ModelTypes, DecodingMethods
import gradio as gr
from PIL import Image

import http.client
import pandas as pd
import numpy as np
import json
import requests
import io
import openpyxl

#from prompt_templates import prompt_input
#from prompt_templates import prompt_input_def

import prompt_templates

prompt_input = prompt_templates.prompt_input
prompt_input_def = prompt_templates.prompt_input_def

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

# Model inference call
model_inference = ModelInference(
    #model_id=ModelTypes.GRANITE_34B_CODE_INSTRUCT,
    model_id=ModelTypes.LLAMA_3_70B_INSTRUCT,
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

def add_dataframe ( query_type):
    if query_type=="SQL Çalıştır":
        return gr.DataFrame(visible=True), gr.Code(language="sql")
    elif query_type=="SQL Açıklamalı":
        return gr.DataFrame(visible=False), gr.Code(language="sql")
    else:
        return gr.DataFrame(visible=False), gr.Code(language="sql")

# Function to classify a single text
def classify_text(text):
    # Replace this with your actual API call
    api_url = "https://ztclassification3-ztclassification.apps.6690d1a7f0f773001e2cf77c.ocp.techzone.ibm.com"
    
    response = requests.post(api_url, json={"text": text})
    result = response.json()
    return pd.DataFrame([{"Text": text, "Label": result["label"], "Score": result["score"]}])

# Function to classify texts from an Excel file
def classify_file(file):
    df = pd.read_excel(file.name)
    results = []
    for text in df.iloc[:, 0]:
        result = classify_text(text).iloc[0]
        results.append(result)
    return pd.DataFrame(results)

import tempfile

# Function to save results to Excel
def save_to_excel(df):
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False)
    output.seek(0)

       # Save the BytesIO content to a temporary file
    temp_file = tempfile.NamedTemporaryFile(delete=False, prefix="ziraat_classified_",suffix='.xlsx')
    temp_file.write(output.read())
    temp_file.close()

    return temp_file.name


iframe_url = "https://web-chat.global.assistant.watson.appdomain.cloud/preview.html?backgroundImageURL=https%3A%2F%2Feu-de.assistant.watson.cloud.ibm.com%2Fpublic%2Fimages%2Fupx-b6be7111-313a-4ea9-81d0-e191261e9f66%3A%3A12d2f1fc-dbcf-4df1-a091-ab6933b57c0a&integrationID=b483e10c-006f-4743-a2d8-7a24ede095a6&region=eu-de&serviceInstanceID=b6be7111-313a-4ea9-81d0-e191261e9f66"
#iframe_url = iframe_url.encode("utf-8")
html_code = f"""
<iframe src="{iframe_url}" style="width:100%; height:500px; border:none;"></iframe>
""" 

# Define the path to your guide image
#image_path = "guest-template.png"  # Replace with your image path
image_path = "images/Ziraat_POC_S4_ER.png"  # Replace with your image path
image_path_ziraat = "images/ziraat_logo.png"
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

with gr.Blocks(js=js_func,theme=theme) as demo:
    
    with gr.Row():  
        image_html1 = gr.HTML(html_img1)

    
    with gr.Tab("Senaryo 4 - DB Entegrasyonu"):
        with gr.Row():
          text_output = gr.Code(label="SQL Kodu", language="sql")
          
          text_result = gr.DataFrame(label="SQL Sorgu Sonuç",interactive=False, visible=False)
        with gr.Row():
          text_input = gr.Textbox(lines=2, label="Soru", scale=3)
          query_type = gr.Dropdown(choices=["SQL", "SQL Açıklamalı", "SQL Çalıştır"], label="Sorgu Tipi Seçiniz", scale=1, value="SQL",interactive=True)
        with gr.Row():  
          text_button = gr.Button("Gönder", variant="primary")
          clear_butoon = gr.ClearButton(components=[text_input,text_output, text_result],value="Temizle", variant="stop" )
       
        examples = gr.Examples(
             examples=[
                  "Bireysl seggmentte kaç müşteri vardır?",
                  "Açık şubeler arasında ATM sayısı en az olan hangisidir?",
                  "Kurumsal&Ticari müşterilerin  en az sahip olduğu ürün nedir?"], 
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
        with gr.Accordion("Daha fazlası için!", open=False):
     
          """ sql_type = gr.Dropdown(
                    ["SQL", "PL/SQL"], label="SQL Tipi"
          ), """
          guide_image = gr.Image(type="pil", value=img, label="Kullanılan DB Şeması")
    
    text_button.click(fn=generate_sql, inputs=[text_input,query_type], outputs=[text_output,text_result])
    query_type.change(fn=add_dataframe, inputs=query_type, outputs=[text_result,text_output])

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

demo.launch( server_name="0.0.0.0", server_port=7860)

