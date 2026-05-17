import requests
from .dtos.ResponseDtos import ResponseObject 
from dotenv import dotenv_values

config = dotenv_values(".env")
inventory_url = config["INVENTORY_SERVICE_URL"]

class ExternalServices:

    @staticmethod
    def create_reservation(reservation_payload):
        query = """
            mutation createReservationMutation($input: CreateReservationInputObject!) {
                createReservationMutation(input: $input) {
                    response {
                        status
                        message
                        id
                    }
                    data {
                        orderId
                        reservedAt
                        id
                    }
                }
            }
        """
        variables = {"input": reservation_payload}

        try:
            response = requests.post(
                inventory_url,
                json={"query": query, "variables": variables},
                headers={"Content-Type": "application/json"}
            )
            response = response.json().get("data", {}).get("createReservationMutation", {}).get("response", {})
            print(response)
            status = response.get("status")
            id = response.get("id")
            return status, id
        except requests.exceptions.HTTPError as errh:
            print(f"Http Error: {errh}")
            return False, None
        except requests.exceptions.ConnectionError as errc:
            print(f"Error Connecting: {errc}")
            return False, None
        except Exception as e:
            return False, None