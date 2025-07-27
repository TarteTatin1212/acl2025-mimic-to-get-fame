import json
import logging
import pandas as pd

from openai import AzureOpenAI
from scripts.scheduler import Scheduler



MODEL_CONFIG_PATH = "basics/config/config_gpt.json"
OUTPUT_PATH = "basics/output/evaluation_results.csv"


if __name__ == "__main__":
    #################
    # setup discussion setting --> move to discussion coordinator?
    #
    num_agents = 3
    # max_chunk_size = 5000

    qmsum_df = pd.read_csv('basics/data/qmsum_test.csv')
    qmsum_df = qmsum_df.head(1)
    
    
    # Set up logging
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)

    #################
    # setup model from config --> move to model handler but call from here
    #
    logger.info("loading model config")
    with open(MODEL_CONFIG_PATH) as config_file:
        config = json.load(config_file)

    API_KEY = config["api_key"]
    API_VERSION = config["api_version"]
    ENDPOINT = config["endpoint"]
    MODEL_NAME = config["model"]

    print(f"Using model: {MODEL_NAME} with endpoint {ENDPOINT}")

    CLIENT = AzureOpenAI(
        api_key=API_KEY,
        api_version= API_VERSION,
        azure_endpoint=ENDPOINT,
    )

    print("client set up")
    scheduler = Scheduler(CLIENT, MODEL_NAME, num_agents)
    generated_summary_df = scheduler.schedule(df=qmsum_df)
    generated_summary_df.to_csv(OUTPUT_PATH, index=False)