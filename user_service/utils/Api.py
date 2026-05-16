import requests
from dto.Response import ResponseObject 
from dotenv import dotenv_values

config = dotenv_values(".env")
email_url = config["EMAIL_SERVICE_URL"]

class ExternalServices:

    @staticmethod
    def send_email(email_payload):
        print(email_url)
        query = """
            mutation SendEmail($input: EmailDataInputObject!) {
                sendEmailMutation(input: $input) {
                    response {
                        status
                        message
                    }
                    data
                }
            }
        """
        variables = {"input": email_payload}

        try:
            requests.post(
                email_url,
                json={"query": query, "variables": variables},
                headers={"Content-Type": "application/json"}
            )
            return True
        except Exception as e:
            print(e)
            return False
