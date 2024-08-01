import json
import time
from typing import Dict, List, Any
import requests
from fuzzywuzzy import process
from datetime import datetime, timedelta


from ibm_watsonx_ai.foundation_models import ModelInference
from ibm_watsonx_ai.metanames import GenTextParamsMetaNames as GenParams
from ibm_watsonx_ai.foundation_models.utils.enums import ModelTypes, DecodingMethods

#from ibm_watsonx_ai.serving import ModelServing
from langchain.chains import LLMChain
from langchain.prompts import PromptTemplate

class WatsonxAI:
    def __init__(self, api_key: str, project_id: str, region: str = "us-south", model: str = "meta-llama/llama-3-405b-instruct"):
        self.model_inference = ModelInference(
            model_id=model,
            credentials={
                "apikey": api_key,
                "url": f"https://{region}.ml.cloud.ibm.com"
            },
            project_id=project_id
        )

    def generate(self, prompt: str, system_prompt: str = "") -> Dict[str, Any]:
        full_prompt = f"{system_prompt}\n\n{prompt}" if system_prompt else prompt

        params = {
            #GenParams.DECODING_METHOD: "sample",
            GenParams.MAX_NEW_TOKENS: 2048,
            GenParams.TEMPERATURE: 0.7
            #GenParams.REPETITION_PENALTY: 1
         
        }

        response = self.model_inference.generate(prompt=full_prompt, params=params)
        return response

class EVDSQueryGenerator:
    def __init__(self, evds_api_key: str, watsonx_api_key: str, watsonx_project_id: str, watsonx_region: str):
        self.evds_api_key = evds_api_key
        self.base_url = "https://evds2.tcmb.gov.tr/service/evds/"
        self.watsonx = WatsonxAI(watsonx_api_key, watsonx_project_id, watsonx_region)
        self.categories = self._get_categories()
        self.datagroups = {}
        self.series = {}

    def _get_categories(self):
        url = f"{self.base_url}categories/type=json"

        headers = {'key': self.evds_api_key}
        max_retries = 5
        for attempt in range(max_retries):
            try:
                response = requests.get(url, headers=headers)
                response.raise_for_status()
                
                print(f"Response status code: {response.status_code}")
                print(f"Response content: {response.text[:500]}...")
                
                categories = response.json()
                return {cat['TOPIC_TITLE_ENG']: str(int(cat['CATEGORY_ID'])) for cat in categories}
            
            except requests.exceptions.RequestException as e:
                print(f"Attempt {attempt + 1} failed: {str(e)}")
                if attempt == max_retries - 1:
                    raise
                time.sleep(10 * (2 ** attempt))
            
            except json.JSONDecodeError:
                print(f"Failed to decode JSON. Response content: {response.text}")
                raise
        
        raise Exception("Failed to fetch categories after multiple attempts")
        pass

    def _get_datagroups(self, category_id: str):
        url = f"{self.base_url}datagroups/mode=2&code={category_id}&type=json"
        response = requests.get(url, headers={'key': self.evds_api_key})
        response.raise_for_status()
        datagroups = response.json()
        print(datagroups)
        return {dg['DATAGROUP_NAME_ENG']: dg['DATAGROUP_CODE'] for dg in datagroups}
        pass

    def _get_series(self, datagroup_code: str):
        url = f"{self.base_url}serieList/code={datagroup_code}?type=json"
        response = requests.get(url, headers={'key': self.evds_api_key})
        response.raise_for_status()
        series = response.json()
        print (series)
        return {s['SERIE_NAME_ENG']: s['SERIE_CODE'] for s in series}
        pass

    def _find_best_match(self, query: str, options: Dict[str, str]) -> str:
        best_match = process.extractOne(query, options.keys())
        return options[best_match[0]]

    def _parse_user_query(self, user_query: str) -> Dict:
        # Step 1: Identify the category
        #print(self.categories)
        category_prompt = f"""
            <|begin_of_text|><|start_header_id|>system<|end_header_id|>
            You are an AI assistant specialized in categorizing user queries. 
            You have been provided with a list of categories, each with a unique integer ID. 
            Your task is to analyze the user's query and determine the most relevant category from the list.:\n
            Given categories:
            {self.categories}\n\n
            Instructions:
            1. Carefully read and understand the user's query.
            2. Compare the query's content and intent to the given categories.
            3. Identify the single most relevant category id that best matches the query.
            4. Return ONLY the integer ID of the chosen category.
            5. Do not provide any explanation or additional text in your response.

            Now, please categorize the following user query by responding with only the relevant category ID:
            leot_id|><|start_header_id|>user<|end_header_id|>
                '{user_query}'\n\n
            <|eot_id |>
            <|start_header_id|>assistant<|end_header_id|>
                """
        #print(category_prompt)
        category_response = self.watsonx.generate(category_prompt)
        #print(category_response['results'][0]['generated_text'].strip())
        category_id = category_response['results'][0]['generated_text'].strip()
        print (category_id)
        
        # Step 2: Identify the datagroup
        self.datagroups = self._get_datagroups(category_id)
        print ("girdi")
        #print (self.datagroups[category_id])
        datagroup_prompt = f"""
            <|begin_of_text|><|start_header_id|>system<|end_header_id|>
            You are an AI assistant specialized in categorizing user queries. 
            You have been provided with a list of datagroups, each with a unique datagroupcode. 
            Your task is to analyze the user's query and determine the most relevant datagroup from the list.:\n
            Given datagrouos for category {category_id}:
            {self.datagroups}\n\n
            Instructions:
            1. Carefully read and understand the user's query.
            2. Compare the query's content and intent to the given datagroups.
            3. Identify the single most relevant datagroup code that best matches the query.
            4. Return ONLY the code of the chosen datagroup.
            5. Do not provide any explanation or additional text in your response.

            Now, please categorize the following user query by responding with only the relevant datagroup:
            leot_id|><|start_header_id|>user<|end_header_id|>
                '{user_query}'\n\n
            <|eot_id |>
            <|start_header_id|>assistant<|end_header_id|>
                """
        
        #print (datagroup_prompt)
        #"Given the following datagroups for category {category_id}:\n{self.datagroups}\n\nIdentify the most relevant single datagroup code for the query: '{user_query}'\n\nRespond with the single datagroup code only, only one line. Sample output: bie_yssk"
        #print (datagroup_prompt)
        datagroup_response = self.watsonx.generate(datagroup_prompt)
        
        datagroup_code = datagroup_response['results'][0]['generated_text'].strip()
        print(datagroup_code)


        # Step 3: Identify the series
        self.series = self._get_series(datagroup_code)
        print (self.series)
        series_prompt = f"""
            <|begin_of_text|><|start_header_id|>system<|end_header_id|>
            You are an AI assistant specialized in categorizing user queries. 
            You have been provided with a list of series, each with a unique series doe. 
            Your task is to analyze the user's query and determine the most relevant series doe from the list.:\n

            Given series  for datagroup code {datagroup_code}:
            {self.series}\n\n
            Instructions:
            1. Carefully read and understand the user's query.
            2. Compare the query's content and intent to the given series codes.
            3. Identify the single most relevant series codes that best matches the query.
            4. Return ONLY the code of the chosen series.
            5. Do not provide any explanation or additional text in your response.

            Now, please categorize the following user query by responding with only the relevant series:
            <leot_id|><|start_header_id|>user<|end_header_id|>
                '{user_query}'\n\n
            <|eot_id |>
            <|start_header_id|>assistant<|end_header_id|>
                """
        
        print (series_prompt)
        #f"Given the following series for datagroup {datagroup_code}:\n{self.series}\n\nIdentify the most relevant series for the query: '{user_query}'\n\nRespond with the series code only."
        series_response = self.watsonx.generate(series_prompt)
        
        series_code = series_response['results'][0]['generated_text'].strip()
        print (series_code)

        # Step 4: Extract date range and other parameters
        params_prompt = f"""
        <|begin_of_text|><|start_header_id|>system<|end_header_id|>
        Given the user query: '{user_query}'
        And the identified series: {series_code}
        Extract dates based on user query.
        Extract the following information:
        1. Start date (in YYYY-MM-DD format)
        2. End date (in YYYY-MM-DD format)
        3. Frequency (daily, business, weekly, semi_monthly, monthly, quarterly, semi_annual, annual)
        4. Aggregation type (avg, min, max, first, last, sum)
        5. Formula (level, percent_change, difference, yoy_percent_change, yoy_difference, ytd_percent_change, ytd_difference, moving_average, moving_sum)

        If any information is not specified in the query, use appropriate defaults or leave blank.
        Respond in JSON format.
        <leot_id|><|start_header_id|>user<|end_header_id|>
        <|eot_id |>
        <|start_header_id|>assistant<|end_header_id|>
        """
        params_response = self.watsonx.generate(params_prompt)
        params = json.loads(params_response['results'][0]['generated_text'])

        # Combine all extracted information
        parsed_query = {
            "series_codes": [series_code],
            "start_date": params.get("start_date", ""),
            "end_date": params.get("end_date", ""),
            "frequency": params.get("frequency", ""),
            "aggregation_type": params.get("aggregation_type", ""),
            "formula": params.get("formula", "")
        }

        return parsed_query
    
    def _build_url(self, parsed_query: Dict) -> str:
        series = "-".join(parsed_query["series_codes"])
        start_date = parsed_query["start_date"].replace("-", "")
        end_date = parsed_query["end_date"].replace("-", "")
        
        url = f"{self.base_url}series={series}&startDate={start_date}&endDate={end_date}"
        print (url)
        
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

    def generate_query(self, user_query: str) -> Dict:
        print (user_query)
        try:
            parsed_query = self._parse_user_query(user_query)
            print (parsed_query)
            if self.validate_input(parsed_query):
                print(parsed_query)
                url = self._build_url(parsed_query)
                return {
                    "url": url,
                    "parsed_query": parsed_query,
                    "explanation": self._generate_explanation(parsed_query)
                }
            else:
                raise ValueError("Invalid input parameters")
        except Exception as e:
            error_message = f"An error occurred: {str(e)}"
            print(error_message)
            return {"error": error_message}

    def validate_input(self, parsed_query: Dict) -> bool:
        required_fields = ["series_codes", "start_date", "end_date"]
        return all(field in parsed_query for field in required_fields)

    def _generate_explanation(self, parsed_query: Dict) -> str:
        explanation = f"Query for EVDS data:\n"
        explanation += f"Series: {', '.join(parsed_query['series_codes'])}\n"
        explanation += f"Date range: {parsed_query['start_date']} to {parsed_query['end_date']}\n"
        
        if "frequency" in parsed_query:
            explanation += f"Frequency: {parsed_query['frequency']}\n"
        if "aggregation_type" in parsed_query:
            explanation += f"Aggregation method: {parsed_query['aggregation_type']}\n"
        if "formula" in parsed_query:
            explanation += f"Formula applied: {parsed_query['formula']}\n"
        
        return explanation

    def execute_query(self, url: str) -> Dict:
        headers = {'key': self.evds_api_key}
        response = requests.get(url, headers=headers)
        return {
            "status_code": response.status_code,
            "content": response.json(),
            "explanation": self._interpret_response(response)
        }

    def _interpret_response(self, response: requests.Response) -> str:
        if response.status_code == 200:
            data = response.json()
            series_name = data['items'][0]['SERIE_NAME']
            start_date = data['items'][0]['UNIXTIME']
            end_date = data['items'][-1]['UNIXTIME']
            num_observations = len(data['items'])
            return f"Successfully retrieved {series_name} data from {start_date} to {end_date}, containing {num_observations} observations."
        else:
            return f"Error retrieving data. Status code: {response.status_code}"

if __name__ == "__main__":
    evds_api_key = "XJwl68qu5U"
    watsonx_api_key = "tI3EoE3dCWtIbATgMcdux-VWWY1mp7t04SCjOLMELiZj"
    watsonx_project_id = "86cc43a6-c2f0-4e3e-a6e9-426ac8cf8f7b"
    watsonx_region = "us-south"  # Change this if your region is different
    
    evds_generator = EVDSQueryGenerator(evds_api_key, watsonx_api_key, watsonx_project_id, watsonx_region)
    print (evds_generator)
    
    user_query = "Get the USD/TRY exchange rate for the last month"
    result = evds_generator.generate_query(user_query)
    
    if "url" in result:
        print("Generated URL:")
        print(result["url"])
        print("\nExplanation:")
        print(result["explanation"])
        
        # Optionally, execute the query
        response = evds_generator.execute_query(result["url"])
        print("\nQuery Result:")
        print(response["explanation"])
    else:
        print("Error occurred:")
        print(result["error"])