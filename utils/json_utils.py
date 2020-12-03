import json
from collections import namedtuple


def find_values(json_repr, id):
    results = []

    def _decode_dict(a_dict):
        try:
            results.append(a_dict[id])
        except KeyError:
            pass
        return a_dict

    json.loads(json_repr, object_hook=_decode_dict)  # Return value ignored.
    return results


class InvalidAutoBuyConfigException(Exception):
    def __init__(self, message):
        super().__init__(message)


def product_loader(product_json):
    # Get the fields that are included in the JSON configuration from the User
    fields = list(product_json.keys())
    # Append any fields required by the code that aren't found in the JSON to the end of the fields
    known_fields = ["name", "asin_list", "reserve", "check_shipping", "used"]
    for field in known_fields:
        if field not in fields:
            fields.append(field)
    product = namedtuple(
        "product", fields, defaults=(None,) * len(product_json.keys())
    )(*product_json.values())
    return product
