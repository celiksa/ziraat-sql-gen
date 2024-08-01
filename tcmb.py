import requests
import functools
from mistralai.models.chat_completion import ChatMessage
from mistralai.client import MistralClient
from mistralai.models.chat_completion import ChatMessage
from langchain_openai import ChatOpenAI
import json
from typing import Dict, List
from evds import evdsAPI
import logging
import os
import requests
import json
from pydantic import BaseModel
from flask_openapi3 import Info, Tag
from flask_openapi3 import OpenAPI
print(os.getcwd())

info = Info(title="Ziraat Teknoloji API", version="1.0.0")
app = OpenAPI(__name__, info=info)
logging.getLogger("unitxt").setLevel(logging.ERROR)


print("uygulama açıldı")

class EVDS:
    def __init__(self, openai_api_key: str, evds_api_key: str, mistral_api_key: str):
        print("sınıf oluşturuldu")
        self.openai_api_key = openai_api_key
        self.mistral_key = mistral_api_key
        self.evds_api_key = evds_api_key
        self.base_url = "https://evds2.tcmb.gov.tr/service/evds/"
        self.headers = {'key': evds_api_key}
        self.evds = evdsAPI(evds_api_key)
        self.categories = self.evds.main_categories
        print("EVDS yaratıldı, kategoriler: ", self.categories)
        self.datagroups = {}
        self.series = {}
        self.main_category_response=""
        self.series = ""
        self.function_name_response=""
        self.series_response=""
        self.sub_category_response=""
        self.function_params_response=""
        self.model=ChatOpenAI(model="gpt-4o-mini", openai_api_key = openai_api_key, max_tokens=200)

    def get_evds(self, startdate, enddate, aggregationtypes="", frequency="", formulas="") -> Dict:
        full_series = ""
        for s in self.series:
            full_series += s["code"] + "-"
        base_url = 'https://evds2.tcmb.gov.tr/service/evds/series=' + full_series +'&startDate='+ startdate +'&endDate='+ enddate
        if len(frequency) > 0:
            frequency_map = {
                "daily": 1, "business": 2, "weekly": 3, "semi_monthly": 4,
                "monthly": 5, "quarterly": 6, "semi_annual": 7, "annual": 8
            }
            f = frequency_map[frequency]
            #base_url = base_url + '&frequency=' + str(f) 
        if len(formulas) > 0:
            formula_map = {
                "level": 0, "percent_change": 1, "difference": 2, "yoy_percent_change": 3,
                "yoy_difference": 4, "ytd_percent_change": 5, "ytd_difference": 6,
                "average": 7, "sum": 8
            }
            o = formula_map[formulas]
            #base_url = base_url + '&formulas=' + str(o) 
        #if len(aggregationtypes) > 0:
         #   base_url = base_url + '&aggregationTypes=' + aggregationtypes 
        headers = {'key':'dKkDaKKiXg'}
        response = requests.get(base_url+'&type=json', headers=headers)
        print(response.content)
        return {
            "status_code": response.status_code,
            "content": response.content
        }
    
    def prompt_generator_sub(self, question, table) -> str:
        prompt_category_detection = """You are a finance expert tasked with analyzing the following finance sentence and selecting the most relevant title from a specified table. Follow these steps:
    **Retrieve Relevant Data**: From the identified table, find the DATAGROUP_CODE and category id that best match the content of the sentence.
    **Finance Sentence:**
    "{question}"
    **Dictionary:**
    {table}
    **Instructions:**
    - Determine the correct table from the dictionary.
    - Use this table to find the DATAGROUP_CODE and category id values that are most relevant to the finance sentence.
    - Ensure that the values retrieved are the best match to the content of the sentence.
    **Conclusion:**
    Provide the result in the following format, only return following information not add any other word or sentence in response, give answer only in JSON Object format, only return answer with the following format do not use different format:
    {{"name": "found_data_group", "code": "data_group_code"}}
    """
        return prompt_category_detection.format(question=question, table=table)
    
    def prompt_generator(self, question, table) -> str:
        prompt_category_detection = """You are a finance expert tasked with analyzing the following finance sentence and selecting the most relevant title from a specified table. Follow these steps:
    **Retrieve Relevant Data**: From the identified table, find the TOPIC_TITLE_TR and category id that best match the content of the sentence.
    **Finance Sentence:**
    "{question}"
    **Dictionary:**
    {table}
    **Instructions:**
    - Determine the correct table from the dictionary.
    - Use this table to find the TOPIC_TITLE_TR and category id values that are most relevant to the finance sentence.
    - Ensure that the values retrieved are the best match to the content of the sentence.
    **Conclusion:**
    Provide the result in the following format, only return following information not add any other word or sentence in response, give answer only in JSON Object format, only return answer with the following format do not use different format:
    {{"category": "found_category", "id": category_id}}
    """
        return prompt_category_detection.format(question=question, table=table)
    
    def prompt_generator_serie(self, question, table) -> str:
        prompt_category_detection = """You are a finance expert tasked with analyzing the following finance sentence and selecting the most relevant title from a specified table. Follow these steps:
    **Retrieve Relevant Data**: From the identified table, find the SERIE_CODE and category id that best match the content of the sentence. If match result have got more than one record return all of them in array list.
    **Finance Sentence:**
    "{question}"
    **Dictionary:**
    {table}
    **Instructions:**
    - Determine the correct table from the dictionary.
    - Use this table to find the SERIE_CODE and category id values that are most relevant to the finance sentence.
    - Ensure that the values retrieved are the best matched records to the content of the sentence.
    **Conclusion:**
    Provide the result in the following format, only return following information not add any other word or sentence in response, give answer only in list Array format, only return answer with the following format do not use different format:
    [{{"name": "SERIE_NAME", "code": SERIE_CODE}}]
    """
        return prompt_category_detection.format(question=question, table=table)

    def _parse_user_query(self, user_query: str) -> str:
        category_prompt = self.prompt_generator(question=user_query, table=self.categories)
        category_response = self.model.invoke(category_prompt)
        category_json = json.loads(category_response.content)
        self.main_category_response = category_response.content
        print("İlk arama sonucunda bulunan değerler:", category_json)
        category_id = category_json["id"]

        prompt_sub_category = self.prompt_generator_sub(question=user_query, table=self.evds.get_sub_categories(category_id))
        response_sub_category =self.model.invoke(prompt_sub_category)
        sub_category_json = json.loads(response_sub_category.content)
        self.sub_category_response = response_sub_category.content
        print("İkinci alt kategori arama sonucunda bulunan değerler:", sub_category_json)
        datagroup = sub_category_json["code"]
 

        prompt_series = self.prompt_generator_serie(question=user_query, table=self.evds.get_series(datagroup))
        response_series = self.model.invoke(prompt_series)
        series_list_json = json.loads(response_series.content)
        self.series_response = response_series.content
        print("Üçüncü seri arama sonucunda bulunan değerler:", series_list_json)
        self.series = series_list_json
        self.tools = [
        {
            "type": "function",
            "function": {
                "name": "evds",
                "description": "Turkish central bank api provide all of the financial needs and information in that api, it serve financial instructions, international finance statuses, money transactions, loans, debits, banking operations or etc, you can found everything for financial area in this api",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "startdate": {
                            "type": "string",
                            "description": "requested transaction start date or time with format dd-MM-yyyy, it is required parameter you must find and return begin date value. If query not contains any start date, you can alternatively set start date as 01-01-2024",
                        },
                        "enddate": {
                            "type": "string",
                            "description": "requested transaction end date or time with format dd-MM-yyyy, it is required parameter you must find and return last date value. If query not contains any end date, you can alternatively set end date as 31-12-2024",
                        },
                        "frequency": {
                            "type": "string",
                            "description": "It indicates how often the data in the series will be fetched. Its definition is optional. If not defined, the default publication frequency defined for the series is used. It can take the following values: 'daily' = 1, 'business' = 2, 'weekly' = 3, 'semi monthly' = 4, 'monthly' = 5, 'quarterly' = 6, 'semi annual' = 7, 'annual' = 8)",
                        },
                        "aggregationtypes": {
                            "type": "string",
                            "description": "Distributes aggregation being used during serial storage. It is optional to define it. If not defined, the default method defined for the series is used. Also worth It can take string or list. In case of string retrieval, the same method is applied for all series. List The specified particles are applied sequentially to the series whose sizes are defined in the series parameters. Available aggregation types are as follows: avg, min, max, first, last, sum)",
                        },
                        "formulas": {
                            "type": "string",
                            "description": "It refers to the formula to be applied when fetching the data in the series. Its definition is optional. If not defined, the default formula defined for the series is used. It can also take string or list as value. In case of string, the same formula is applied for all series. If series is defined as a list The formulas specified in the series are applied respectively to the series defined in the parameter. The methods that can be used are as follows: like this: level, percent_change, difference, yoy_percent_change, yoy_difference, ytd_percent_change, ytd_difference, average, sum",
                        }
                    },
                    "required": ["startdate"],
                    "required": ["enddate"]
                },
            },
        },
    ]
        return response_series.content
    
    def _build_url(self, parsed_query: Dict) -> str:
        series = "-".join(parsed_query["series_codes"])
        start_date = parsed_query["start_date"].replace("-", "")
        end_date = parsed_query["end_date"].replace("-", "")
        
        url = f"{self.base_url}series={series}&startDate={start_date}&endDate={end_date}"
        print ("URLurl"+url)
        
        if "frequency" in parsed_query:
            frequency_map = {
                "daily": 1, "business": 2, "weekly": 3, "semi_monthly": 4,
                "monthly": 5, "quarterly": 6, "semi_annual": 7, "annual": 8
            }
            url += f"&frequency={frequency_map[parsed_query['frequency']]}"
        
        if "aggregation_type" in parsed_query:
            url += f"&aggregationTypes={parsed_query['aggregation_type']}"
        
        if "formula" in parsed_query:
            formula_map = {
                "level": 0, "percent_change": 1, "difference": 2, "yoy_percent_change": 3,
                "yoy_difference": 4, "ytd_percent_change": 5, "ytd_difference": 6,
                "moving_average": 7, "moving_sum": 8
            }
            url += f"&formulas={formula_map[parsed_query['formula']]}"
        
        url += "&type=json"
        return url

    def tool_calling(self, series, query) -> str:
        response = ""
        series = series
        model = "mistral-large-latest"
        api_key=self.mistral_key

        names_to_functions = {
                'evds': functools.partial(self.get_evds),
            }

        messages = [
                ChatMessage(role="user", content=query)
            ]

        client = MistralClient(api_key=api_key)
        response = client.chat(model=model, messages=messages, tools=self.tools, tool_choice="auto")
        messages.append(response.choices[0].message)
        tool_call = response.choices[0].message.tool_calls[0]
        function_name = tool_call.function.name
        function_params = json.loads(tool_call.function.arguments)
        if self.validate_input(function_params):
            print("\nfunction_name: ", function_name, "\nfunction_params: ", function_params)
            self.function_name_response = function_name
            self.function_params_response = function_params
            function_result = names_to_functions[function_name](**function_params)
            messages.append(ChatMessage(role="tool", name=function_name, content=function_result["content"], tool_call_id=tool_call.id))
            response = client.chat(model=model, messages=messages)
        else:
            raise ValueError("Invalid input parameters")
        return response.choices[0].message.content

    def generate_query(self, user_query: str)  -> str:
        try:
            self._parse_user_query(user_query)
            return self.tool_calling(user_query)
        except Exception as e:
            error_message = f"An error occurred: {str(e)}"
            print(error_message)
            return {"error": error_message}

    def validate_input(self, parsed_query: Dict) -> bool:
        required_fields = ["startdate", "enddate"]
        return all(field in parsed_query for field in required_fields)       

tcmb_tag = Tag(name="llm", description="LLM Api for Ziraat Teknoloji")

class ModelQuery(BaseModel):
    text: str
    key: str

#@app.post("/", summary="get tcmb recommendation with llm", tags=[tcmb_tag])
def index(model_query, api):
    try:
        print('web servis başlatıldı')
        #input = json.load(model_query)
        data = model_query
        key = api
        query = data
        evds_generator = EVDS(key, "dKkDaKKiXg", "0tTRw7npPNMkCH5LGw1pWcTdFd9bw2z5")
        parsed_query = evds_generator._parse_user_query(user_query=query)
        series_list_json = json.loads(parsed_query)
        result = evds_generator.tool_calling(series_list_json, query)
        return {'generated_answer': result,
                'founded_series': evds_generator.series_response,
                'founded_main_categories': evds_generator.main_category_response,
                'founded_sub_categories': evds_generator.sub_category_response,
                'selected_function_name': evds_generator.function_name_response,
                'extracted_parameters': evds_generator.function_params_response }
    except Exception as e:
        print(e)
        logging.exception(e)
        return {'unexpected_exception': e }
    


#if __name__ == '__main__':
#	app.run(debug=True, host='0.0.0.0', port=8000)