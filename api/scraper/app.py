import json
from typing import Any, Dict, Optional

from common.schemas import LambdaResponse
from scraper.src.apify_webhook import process_apify_webhook


def lambda_handler(event: Optional[Any], context: Optional[Any]) -> LambdaResponse:
    try:
        body: Dict[str, Any] = json.loads(event['body'])
    except TypeError:
        body: Dict[str, Any] = event['body']

    # get event type
    event_type = body['event_type']

    if event_type == "apify_webhook":
        process_apify_webhook(body['data'])
    else:
        raise ValueError("Invalid event type")

    return {
        "statusCode": 200,
        "body": {
            "message": "Success",
        },
    }


if __name__ == "__main__":
    print(lambda_handler({
        "body": {
            "event_type": "apify_webhook",
            "data": {
                "eventType": "ACTOR.RUN.SUCCEEDED",
                "userId": "oeiQgfg5fsmIJB7Cn",
                "actorId": "aYG0l9s7dbB7j3gbS",
                "actorTaskId": "If task was used, its ID.",
                "actorRunId": "AV2l9u1VM08cP4vxk",
                "startedAt": "2021-09-01T13:00:00.000Z",
                "finishedAt": "2021-09-01T13:00:00.000Z",
            }
        }
    }, None))
