import logging
import sys
import os

from dynamic_dns import DynamicDNS

if __name__ == "__main__":

    # Set up logging
    # Logging to stdout probably isn't the best but since I am using
    # unraid for this, it makes sense.
    logging.basicConfig(
        format="%(asctime)s %(levelname)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        stream=sys.stdout,
        level=logging.DEBUG,
    )
    logging.getLogger("botocore").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)

    try:
        hosted_zone_name = os.environ["HOSTED_ZONE_NAME"]
        resource_record_name = os.environ["RESOURCE_RECORD_NAME"]
        health_check_url = os.environ.get("HEALTH_CHECK_URL")
        dyn_dns = DynamicDNS()
        dyn_dns.run(hosted_zone_name, resource_record_name, health_check_url)

    except:
        logging.exception("Error Running DynamicDNS")
