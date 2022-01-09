import typing
import boto3
import urllib.request
import logging


class DynamicDNS:
    """
    A class responsible for updating a single record within an AWS Route53 hosted zone.
    """

    def __init__(self):
        """
        Initializes the class by instantiating the boto3 client.
        """
        self._client = boto3.client("route53")

    def run(
        self,
        hosted_zone_name: str,
        resource_record_name: str,
        health_check_url: typing.Optional[str] = None,
    ) -> None:
        """
        Runs the updater with the provided hosted_zone_name and resource_record_name.  Upon completion, the
        health_check_url will be pinged if provided.

        :param hosted_zone_name: The name of the Route53 zone. It should be noted these must have the trailing period
        :param resource_record_name: The name of the record.  It should be noted these must have the trailing period
        :param health_check_url: The url of the healthcheck.

        :precondition: len(hosted_zone_name) > 0
        :precondition: len(resource_record_name) > 0
        :precondition: health_check_url is None or len(health_check_url) > 0

        :precondition: hosted_zone_name[-1] == '.'
        :precondition: resource_record_name[-1] == '.'
        """
        assert isinstance(hosted_zone_name, str)
        assert isinstance(resource_record_name, str)
        assert health_check_url is None or isinstance(health_check_url, str)
        assert hosted_zone_name[-1] == "."
        assert resource_record_name[-1] == "."

        hosted_zone_id = self._get_hosted_zone_id(hosted_zone_name)
        resource_record_set = self._get_resource_record_set(
            hosted_zone_id, resource_record_name
        )
        route_53_ip = resource_record_set["ResourceRecords"][0]["Value"]
        current_ip = DynamicDNS._get_public_ip()

        logging.debug(f"Route 53 Ip: {route_53_ip} || Current Ip: {current_ip}")

        if current_ip == route_53_ip:
            logging.debug("No change detected. Aborting")
        else:
            logging.debug("Change detected. Updating.")
            self._update_ip(hosted_zone_id, resource_record_name, current_ip)

        if health_check_url:
            self._ping_health_check(health_check_url)

    def _update_ip(self, hosted_zone_id, resource_record_name, new_ip):
        """
        Updates Route53 using the hosted_zone_id and resource_record_name with the new_ip.

        :precondition: len(hosted_zone_id) > 0
        :precondition: len(resource_record_name) > 0
        :precondition: len(new_ip) > 0
        """
        assert isinstance(hosted_zone_id, str)
        assert len(hosted_zone_id) > 0
        assert isinstance(resource_record_name, str)
        assert len(resource_record_name) > 0
        assert resource_record_name[-1] == "."
        assert isinstance(new_ip, str)
        assert len(new_ip) > 0

        self._client.change_resource_record_sets(
            HostedZoneId=hosted_zone_id,
            ChangeBatch={
                "Comment": "Automatic DNS update",
                "Changes": [
                    {
                        "Action": "UPSERT",
                        "ResourceRecordSet": {
                            "Name": resource_record_name,
                            "Type": "A",
                            "TTL": 180,
                            "ResourceRecords": [
                                {"Value": new_ip},
                            ],
                        },
                    },
                ],
            },
        )

    def _ping_health_check(self, url: str) -> None:
        """
        Pings the health check url to indicate a successful run. An exception will be
        raised if anything other than a 200 response status code is returned.

        :precondition: len(url) > 0
        """
        assert isinstance(url, str)
        assert len(url) > 0

        response = urllib.request.urlopen(url)
        status_code = response.getcode()

        if status_code != 200:
            raise Exception(f"Unable To Ping Health Check: {status_code}")

    def _get_resource_record_set(
        self, hosted_zone_id: str, resource_record_name: str
    ) -> typing.Dict[str, typing.Any]:
        """
        Selects and returns a dictionary representation of a resource record set by name, if it exists,
        otherwise raises an error

        :precondition: len(hosted_zone_id) > 0
        :precondition: resource_record_name[-1] == '.'
        """
        assert isinstance(hosted_zone_id, str)
        assert len(hosted_zone_id) > 0
        assert isinstance(resource_record_name, str)
        assert len(resource_record_name) > 0
        assert resource_record_name[-1] == "."

        paginator = self._client.get_paginator("list_resource_record_sets")

        source_zone_records = paginator.paginate(HostedZoneId=hosted_zone_id)
        for record_set in source_zone_records:
            for record in record_set["ResourceRecordSets"]:
                if record["Type"] == "A" and record["Name"] == resource_record_name:

                    # Sanity check, should only ever contain one
                    assert len(record["ResourceRecords"]) == 1
                    return record
        raise Exception("Unable to find resource record set")

    def _get_hosted_zone_id(self, hosted_zone_name: str) -> str:
        """
        Returns the hosted zone id by hosted zone name, if it exists, otherwise raises an error.

        :param hosted_zone_name: The name of the Route53 zone.

        :precondition: len(hosted_zone_name) > 0
        :precondition: hosted_zone_name[-1] == '.'
        """
        assert isinstance(hosted_zone_name, str)
        assert len(hosted_zone_name) > 0

        response = self._client.list_hosted_zones()
        for hosted_zone in response["HostedZones"]:
            if hosted_zone["Name"] == hosted_zone_name:
                return hosted_zone["Id"]
        raise Exception("Unable to find hosted zone")

    @staticmethod
    def _get_public_ip() -> str:
        """
        Returns the public IP address, as a string, using a 3rd party site.
        """
        response = urllib.request.urlopen("https://icanhazip.com/")
        ip = response.read()  # Read the contents
        ip = ip.strip()  # Remove the new line character
        ip = ip.decode("utf-8")  # Convert from bytes to string
        return ip
