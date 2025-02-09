from enum import Enum


class AmazonItemCondition(Enum):
    # See https://sellercentral.amazon.com/gp/help/external/200386310?language=en_US&ref=efph_200386310_cont_G1831
    New = 10
    Renewed = 20
    Refurbished = 20
    Rental = 30
    Open_box = 40
    UsedLikeNew = 40
    UsedVeryGood = 50
    UsedGood = 60
    UsedAcceptable = 70
    CollectibleLikeNew = 40
    CollectibleVeryGood = 50
    CollectibleGood = 60
    CollectibleAcceptable = 70
    Unknown = 1000

    @classmethod
    def from_str(cls, label):
        # Straight lookup
        try:
            condition = AmazonItemCondition[label]
            return condition
        except KeyError:
            # Key doesn't exist as a Member, so try cleaning up the string
            cleaned_label = "".join(label.split())
            cleaned_label = cleaned_label.replace("-", "")
            try:
                condition = AmazonItemCondition[cleaned_label]
                return condition
            except KeyError:
                raise NotImplementedError


def get_item_condition(form_action) -> AmazonItemCondition:
    """Attempts to determine the Item Condition from the Add To Cart form action"""
    if "_new_" in form_action:
        # log.debug(f"Item condition is new")
        return AmazonItemCondition.New
    elif "_used_" in form_action:
        # log.debug(f"Item condition is used")
        return AmazonItemCondition.UsedGood
    elif "_col_" in form_action:
        # log.debug(f"Item condition is collectible")
        return AmazonItemCondition.CollectibleGood
    else:
        # log.debug(f"Item condition is unknown: {form_action}")
        return AmazonItemCondition.Unknown
