import datetime
from copy import deepcopy
from datetime import timedelta

from ciso8601 import parse_datetime
from freezegun import freeze_time

from openprocurement.api.tests.base import change_auth
from openprocurement.api.utils import get_now
from openprocurement.framework.electroniccatalogue.tests.base import (
    test_electronicCatalogue_data,
    ban_milestone_data,
    disqualification_milestone_data,
    ban_milestone_data_with_documents,
    disqualification_milestone_data_with_documents,
)
from openprocurement.framework.electroniccatalogue.utils import CONTRACT_BAN_DURATION, MILESTONE_CONTRACT_STATUSES


def create_agreement(self):
    response = self.app.patch_json(
        f"/qualifications/{self.qualification_id}?acc_token={self.framework_token}",
        {"data": {"status": "active"}},
    )
    self.assertEqual(response.status, "200 OK")
    self.assertEqual(response.content_type, "application/json")
    self.assertEqual(response.json["data"]["status"], "active")
    qualification_data = response.json["data"]

    # Check framework was updated
    response = self.app.get(f"/frameworks/{self.framework_id}")
    self.assertEqual(response.status, "200 OK")
    framework_data = response.json["data"]
    self.assertIsNotNone(framework_data["agreementID"])

    # Check agreement was created with correct data
    agreementID = self.agreement_id = framework_data["agreementID"]
    response = self.app.get(f"/agreements/{agreementID}")
    self.assertEqual(response.status, "200 OK")
    agreement_data = response.json["data"]
    self.assertEqual(agreement_data["frameworkID"], framework_data["id"])
    self.assertEqual(agreement_data["agreementType"], framework_data["frameworkType"])
    self.assertEqual(agreement_data["classification"], framework_data["classification"])
    self.assertEqual(agreement_data["additionalClassifications"], framework_data["additionalClassifications"])
    self.assertEqual(agreement_data["procuringEntity"], framework_data["procuringEntity"])
    self.assertEqual(agreement_data["period"]["endDate"], framework_data["qualificationPeriod"]["endDate"])
    self.assertEqual(agreement_data.get("frameworkDetails"), framework_data.get("frameworkDetails"))
    self.assertEqual(agreement_data["status"], "active")
    self.assertAlmostEqual(
        parse_datetime(agreement_data["period"]["startDate"]),
        parse_datetime(qualification_data["date"]),
        delta=datetime.timedelta(60)
    )

    # Check contract was created and created with correct data
    response = self.app.get(f"/submissions/{self.submission_id}")
    submission_data = response.json["data"]

    self.assertIsNotNone(agreement_data.get("contracts"))
    self.assertEqual(len(agreement_data["contracts"]), 1)

    contract_data = agreement_data["contracts"][0]
    self.assertEqual(contract_data["status"], "active")
    self.assertEqual(contract_data["suppliers"], submission_data["tenderers"])
    self.assertEqual(contract_data["qualificationID"], self.qualification_id)

    self.assertIsNotNone(contract_data.get("milestones"))
    self.assertEqual(len(contract_data["milestones"]), 1)
    self.assertEqual(contract_data["milestones"][0]["type"], "activation")
    self.assertEqual(contract_data["milestones"][0]["documents"], qualification_data["documents"])
    self.assertIsNone(contract_data["milestones"][0].get("dueDate"))


def change_agreement(self):
    new_endDate = (
            parse_datetime(test_electronicCatalogue_data["qualificationPeriod"]["endDate"]) - timedelta(days=1)
    ).isoformat()

    response = self.app.patch_json(
        f"/frameworks/{self.framework_id}?acc_token={self.framework_token}",
        {"data": {"qualificationPeriod": {"endDate": new_endDate}}}
    )
    self.assertEqual(response.status, "200 OK")
    self.assertEqual(response.content_type, "application/json")
    self.assertEqual(response.json["data"]["qualificationPeriod"]["endDate"], new_endDate)

    response = self.app.get(f"/agreements/{self.agreement_id}")
    self.assertEqual(response.status, "200 OK")
    self.assertEqual(response.content_type, "application/json")
    self.assertEqual(response.json["data"]["period"]["endDate"], new_endDate)

    new_procuringEntity = deepcopy(test_electronicCatalogue_data["procuringEntity"])
    new_procuringEntity["contactPoint"]["telephone"] = "+380440000000"
    response = self.app.patch_json(
        f"/frameworks/{self.framework_id}?acc_token={self.framework_token}",
        {"data": {"procuringEntity": new_procuringEntity}}
    )
    self.assertEqual(response.status, "200 OK")
    self.assertEqual(response.content_type, "application/json")
    self.assertEqual(response.json["data"]["procuringEntity"], new_procuringEntity)

    response = self.app.get(f"/agreements/{self.agreement_id}")
    self.assertEqual(response.status, "200 OK")
    self.assertEqual(response.content_type, "application/json")
    self.assertEqual(response.json["data"]["procuringEntity"], new_procuringEntity)


def patch_contract_suppliers(self):
    response = self.app.patch_json(
        f"/agreements/{self.agreement_id}/contracts/{self.contract_id}?acc_token={'0' * 32}",
        {"data": {}},
        status=403,
    )
    self.assertEqual(response.status, "403 Forbidden")
    self.assertEqual(response.content_type, "application/json")
    self.assertEqual(
        response.json["errors"],
        [{"location": "url", "name": "permission", "description": "Forbidden"}]
    )

    with change_auth(self.app, ("Basic", ("broker1", ""))):
        response = self.app.patch_json(
            f"/agreements/{self.agreement_id}/contracts/{self.contract_id}?acc_token={self.framework_token}",
            {"data": {}},
            status=403,
        )
        self.assertEqual(response.status, "403 Forbidden")
        self.assertEqual(response.content_type, "application/json")
        self.assertEqual(
            response.json["errors"],
            [{"location": "url", "name": "permission", "description": "Forbidden"}]
        )

    response = self.app.patch_json(
        f"/agreements/{self.agreement_id}/contracts/{self.contract_id}?acc_token={self.framework_token}",
        {"data": {"suppliers": self.initial_submission_data["tenderers"] * 2}},
        status=422,
    )
    self.assertEqual(response.status, "422 Unprocessable Entity")
    self.assertEqual(response.content_type, "application/json")
    self.assertEqual(
        response.json["errors"],
        [{"location": "body", "name": "suppliers", "description": ["Contract must have only one supplier"]}]
    )

    contract_ignore_patch_fields = {
        "id": f"{'0' * 32}",
        "qualificationID": "",
        "status": "unsuccessful",
        "milestones": [{"type": "ban"}],
        "date": "2020-03-10T01:00:20.514000+02:00",
        "suppliers": [{
            "scale": "large",
            "name": "new_name",
            "name_en": "new_name",
            "name_ru": "new_name",
            "identifier": {"scheme": "UA-EDR", "id": "00000001", "legalName": "new_legalName"},
        }]
    }
    contract_data = self.app.get(f"/agreements/{self.agreement_id}/contracts/{self.contract_id}").json["data"]
    response = self.app.patch_json(
        f"/agreements/{self.agreement_id}/contracts/{self.contract_id}?acc_token={self.framework_token}",
        {"data": contract_ignore_patch_fields},
    )
    self.assertEqual(response.status, "200 OK")
    self.assertEqual(response.content_type, "application/json")
    for field in contract_ignore_patch_fields:
        self.assertEqual(response.json["data"].get(field), contract_data.get(field))

    contract_patch_fields = {
        "suppliers": [{
            "address": {
                "countryName": "Україна",
                "postalCode": "01221",
                "region": "Київська область",
                "locality": "Київська область",
                "streetAddress": "вул. Банкова, 11, корпус 2"
            },
            "contactPoint": {
                "name": "Найновіше державне управління справами",
                "name_en": "New state administration",
                "telephone": "0440000001"
            },
        }]
    }
    response = self.app.patch_json(
        f"/agreements/{self.agreement_id}/contracts/{self.contract_id}?acc_token={self.framework_token}",
        {"data": contract_patch_fields},
    )
    self.assertEqual(response.status, "200 OK")
    self.assertEqual(response.content_type, "application/json")
    self.assertTrue(len(response.json["data"]["suppliers"]), 1)
    for field in contract_patch_fields["suppliers"][0]:
        self.assertEqual(response.json["data"]["suppliers"][0].get(field),
                         contract_patch_fields["suppliers"][0].get(field))


def patch_agreement_terminated_status(self):
    response = self.app.patch_json(
        f"/frameworks/{self.framework_id}?acc_token={self.framework_token}",
        {"data": {
            "qualificationPeriod": {"endDate": (get_now() + timedelta(days=CONTRACT_BAN_DURATION-1)).isoformat()}
        }}
    )
    self.assertEqual(response.status, "200 OK")
    self.assertEqual(response.content_type, "application/json")
    response = self.app.get(f"/agreements/{self.agreement_id}")
    self.assertEqual(response.status, "200 OK")
    next_check = response.json["data"]["next_check"]

    with freeze_time((parse_datetime(next_check) + timedelta(hours=1)).isoformat()):
        self.check_chronograph()
    response = self.app.get(f"/agreements/{self.agreement_id}")
    self.assertEqual(response.status, "200 OK")
    self.assertEqual(response.json["data"]["status"], "terminated")
    self.assertIsNone(response.json["data"].get("next_check"))


def patch_contract_active_status(self):
    response = self.app.post_json(
        f"/agreements/{self.agreement_id}/contracts/{self.contract_id}/milestones?acc_token={self.framework_token}",
        {"data": {"type": "ban"}}
    )
    self.assertEqual(response.status, "201 Created")
    response = self.app.get(f"/agreements/{self.agreement_id}/contracts/{self.contract_id}")
    self.assertEqual(response.status, "200 OK")
    self.assertEqual(response.json["data"]["status"], "banned")

    response = self.app.patch_json(
        f"/frameworks/{self.framework_id}?acc_token={self.framework_token}",
        {"data": {
            "qualificationPeriod": {"endDate": (get_now() + timedelta(days=CONTRACT_BAN_DURATION+1)).isoformat()}
        }}
    )
    self.assertEqual(response.status, "200 OK")
    self.assertEqual(response.content_type, "application/json")
    response = self.app.get(f"/agreements/{self.agreement_id}")
    self.assertEqual(response.status, "200 OK")
    next_check = response.json["data"]["next_check"]
    self.assertEqual(response.json["data"]["contracts"][0]["status"], "banned")

    with freeze_time((parse_datetime(next_check) + timedelta(hours=1)).isoformat()):
        self.check_chronograph()
    response = self.app.get(f"/agreements/{self.agreement_id}")
    self.assertEqual(response.status, "200 OK")
    self.assertEqual(response.json["data"]["status"], "active")
    self.assertEqual(response.json["data"]["contracts"][0]["status"], "active")

    response = self.app.post_json(
        "/submissions",
        {"data": self.initial_submission_data},
    )
    self.assertEqual(response.status, "201 Created")
    self.assertEqual(response.content_type, "application/json")
    submission_id = response.json["data"]["id"]
    submission_token = response.json["access"]["token"]

    response = self.app.patch_json(
        f"/submissions/{submission_id}?acc_token={submission_token}",
        {"data": {"status": "active"}},
        status=403,
    )
    self.assertEqual(response.status, "403 Forbidden")
    self.assertEqual(response.content_type, "application/json")
    self.assertEqual(
        response.json["errors"],
        [{'description': "Tenderer can't activate submission with active/banned contract "
                         f'in agreement for framework {self.framework_id}',
          'location': 'body',
          'name': 'data'}]
    )


def patch_several_contracts_active_status(self):
    response = self.app.patch_json(
        f"/frameworks/{self.framework_id}?acc_token={self.framework_token}",
        {"data": {
            "qualificationPeriod": {"endDate": (get_now() + timedelta(days=CONTRACT_BAN_DURATION+3)).isoformat()}
        }}
    )
    self.assertEqual(response.status, "200 OK")
    self.assertEqual(response.content_type, "application/json")
    response = self.app.get(f"/agreements/{self.agreement_id}")
    self.assertEqual(response.status, "200 OK")

    base_identifier_id = self.initial_submission_data["tenderers"][0]["identifier"]["id"]
    for shift, milestone_type, identifier_id in [
        (0, "ban", "00037257"),
        (24, "disqualification", "00037258"),
        (36, "disqualification", "00037259"),
        (48, "ban", "00037260"),
    ]:
        self.initial_submission_data["tenderers"][0]["identifier"]["id"] = identifier_id
        self.create_submission()

        response = self.app.patch_json(
            f"/submissions/{self.submission_id}?acc_token={self.submission_token}",
            {"data": {"status": "active"}}
        )
        self.assertEqual(response.status, "200 OK")
        qualification_id = response.json["data"]["qualificationID"]
        response = self.app.patch_json(
            f"/qualifications/{qualification_id}?acc_token={self.framework_token}",
            {"data": {"status": "active"}}
        )
        self.assertEqual(response.status, "200 OK")
        response = self.app.get(f"/agreements/{self.agreement_id}")
        self.assertEqual(response.status, "200 OK")
        contract_id = response.json["data"]["contracts"][-1]["id"]
        with freeze_time((get_now() + timedelta(hours=shift)).isoformat()):
            response = self.app.post_json(
                f"/agreements/{self.agreement_id}/contracts/{contract_id}/milestones?acc_token={self.framework_token}",
                {"data": {"type": milestone_type}}
            )
    self.initial_submission_data["tenderers"][0]["identifier"]["id"] = base_identifier_id
    response = self.app.get(f"/agreements/{self.agreement_id}")
    self.assertEqual(response.status, "200 OK")
    contract_statuses = [contract["status"] for contract in response.json["data"]["contracts"]]
    self.assertEqual(contract_statuses, ["active", "banned", "unsuccessful", "unsuccessful", "banned"])

    next_check = parse_datetime(response.json["data"]["next_check"])
    with freeze_time((next_check + timedelta(hours=2)).isoformat()):
        self.check_chronograph()
        response = self.app.get(f"/agreements/{self.agreement_id}")
        self.assertEqual(response.status, "200 OK")
        self.assertEqual(response.json["data"]["status"], "active")
        contract_statuses = [contract["status"] for contract in response.json["data"]["contracts"]]
        self.assertEqual(contract_statuses, ["active", "active", "unsuccessful", "unsuccessful", "banned"])

    with freeze_time((next_check + timedelta(hours=26)).isoformat()):
        self.check_chronograph()
        response = self.app.get(f"/agreements/{self.agreement_id}")
        self.assertEqual(response.status, "200 OK")
        self.assertEqual(response.json["data"]["status"], "active")
        contract_statuses = [contract["status"] for contract in response.json["data"]["contracts"]]
        self.assertEqual(contract_statuses, ["active", "active", "unsuccessful", "unsuccessful", "banned"])

    with freeze_time((next_check + timedelta(hours=38)).isoformat()):
        self.check_chronograph()
        response = self.app.get(f"/agreements/{self.agreement_id}")
        self.assertEqual(response.status, "200 OK")
        self.assertEqual(response.json["data"]["status"], "active")
        contract_statuses = [contract["status"] for contract in response.json["data"]["contracts"]]
        self.assertEqual(contract_statuses, ["active", "active", "unsuccessful", "unsuccessful", "banned"])

    with freeze_time((next_check + timedelta(hours=51)).isoformat()):
        self.check_chronograph()
        response = self.app.get(f"/agreements/{self.agreement_id}")
        self.assertEqual(response.status, "200 OK")
        self.assertEqual(response.json["data"]["status"], "terminated")
        contract_statuses = [contract["status"] for contract in response.json["data"]["contracts"]]
        self.assertEqual(contract_statuses, ["terminated", "terminated", "unsuccessful", "unsuccessful", "banned"])


def post_milestone_invalid(self):
    milestone_data = deepcopy(ban_milestone_data)
    response = self.app.post_json(
        f"/agreements/{self.agreement_id}/contracts/{self.contract_id}/milestones?acc_token={'0' * 32}",
        {"data": milestone_data},
        status=403,
    )
    self.assertEqual(response.status, "403 Forbidden")
    self.assertEqual(response.content_type, "application/json")
    self.assertEqual(
        response.json["errors"],
        [{"location": "url", "name": "permission", "description": "Forbidden"}]
    )

    with change_auth(self.app, ("Basic", ("broker1", ""))):
        response = self.app.post_json(
            f"/agreements/{self.agreement_id}/contracts/{self.contract_id}/milestones?acc_token={self.framework_token}",
            {"data": milestone_data},
            status=403,
        )
        self.assertEqual(response.status, "403 Forbidden")
        self.assertEqual(response.content_type, "application/json")
        self.assertEqual(
            response.json["errors"],
            [{"location": "url", "name": "permission", "description": "Forbidden"}]
        )

    milestone_data = {"type": "other_type"}
    response = self.app.post_json(
        f"/agreements/{self.agreement_id}/contracts/{self.contract_id}/milestones?acc_token={self.framework_token}",
        {"data": milestone_data},
        status=422,
    )
    self.assertEqual(response.status, "422 Unprocessable Entity")
    self.assertEqual(response.content_type, "application/json")
    self.assertEqual(
        response.json["errors"],
        [
            {
                "location": "body",
                "name": "type",
                "description": [
                    "Value must be one of ['activation', 'ban', 'disqualification', 'terminated']."
                ]
            }
        ]
    )
    milestone_data = {"type": "activation"}
    response = self.app.post_json(
        f"/agreements/{self.agreement_id}/contracts/{self.contract_id}/milestones?acc_token={self.framework_token}",
        {"data": milestone_data},
        status=403,
    )
    self.assertEqual(response.status, "403 Forbidden")
    self.assertEqual(response.content_type, "application/json")
    self.assertEqual(
        response.json["errors"],
        [
            {
                "location": "body",
                "name": "data",
                "description": "Can't add object for 'activation' milestone"
            }
        ]
    )


def post_ban_milestone(self):
    milestone_data = deepcopy(ban_milestone_data)
    milestone_data["dateModified"] = "2020-03-10T01:00:20.514000+02:00"
    milestone_data["dueDate"] = "2020-03-10T01:00:20.514000+02:00"
    response = self.app.post_json(
        f"/agreements/{self.agreement_id}/contracts/{self.contract_id}/milestones?acc_token={self.framework_token}",
        {"data": milestone_data}
    )
    self.assertEqual(response.status, "201 Created")
    self.assertEqual(response.content_type, "application/json")
    milestone = response.json["data"]
    self.assertEqual(milestone["type"], milestone_data["type"])
    self.assertIsNotNone(milestone["dateModified"])
    self.assertNotEqual(milestone["dateModified"], milestone_data["dateModified"])
    self.assertIsNotNone(milestone["dueDate"])
    self.assertNotEqual(milestone["dueDate"], milestone_data["dueDate"])
    self.assertTrue(parse_datetime(milestone["dueDate"]) - get_now() >= timedelta(days=CONTRACT_BAN_DURATION))

    contract = self.app.get(f"/agreements/{self.agreement_id}/contracts/{self.contract_id}").json["data"]
    self.assertEqual(contract["status"], MILESTONE_CONTRACT_STATUSES[milestone["type"]])

    milestone_data = deepcopy(ban_milestone_data)
    response = self.app.post_json(
        f"/agreements/{self.agreement_id}/contracts/{self.contract_id}/milestones?acc_token={self.framework_token}",
        {"data": milestone_data},
        status=403,
    )
    self.assertEqual(response.status, "403 Forbidden")
    self.assertEqual(response.content_type, "application/json")
    self.assertEqual(
        response.json["errors"],
        [{
            "name": "data",
            "location": "body",
            "description": "Can't add ban milestone for contract in banned status",
          }]

    )


def post_ban_milestone_with_documents(self):
    milestone_data = deepcopy(ban_milestone_data_with_documents)
    milestone_data["documents"][0]["url"] = self.generate_docservice_url()
    milestone_data["dateModified"] = "2020-03-10T01:00:20.514000+02:00"
    milestone_data["dueDate"] = "2020-03-10T01:00:20.514000+02:00"
    response = self.app.post_json(
        f"/agreements/{self.agreement_id}/contracts/{self.contract_id}/milestones?acc_token={self.framework_token}",
        {"data": milestone_data}
    )
    self.assertEqual(response.status, "201 Created")
    self.assertEqual(response.content_type, "application/json")
    milestone = response.json["data"]
    self.assertEqual(milestone["type"], milestone_data["type"])
    self.assertIsNotNone(milestone["dateModified"])
    self.assertNotEqual(milestone["dateModified"], milestone_data["dateModified"])
    self.assertIsNotNone(milestone["dueDate"])
    self.assertNotEqual(milestone["dueDate"], milestone_data["dueDate"])
    self.assertEqual(len(milestone["documents"]), len(milestone_data["documents"]))
    self.assertTrue(parse_datetime(milestone["dueDate"]) - get_now() >= timedelta(days=CONTRACT_BAN_DURATION))

    contract = self.app.get(f"/agreements/{self.agreement_id}/contracts/{self.contract_id}").json["data"]
    self.assertEqual(contract["status"], MILESTONE_CONTRACT_STATUSES[milestone["type"]])


def post_disqualification_milestone(self):
    milestone_data = deepcopy(disqualification_milestone_data)
    milestone_data["dateModified"] = "2020-03-10T01:00:20.514000+02:00"
    milestone_data["dueDate"] = "2020-03-10T01:00:20.514000+02:00"
    response = self.app.post_json(
        f"/agreements/{self.agreement_id}/contracts/{self.contract_id}/milestones?acc_token={self.framework_token}",
        {"data": milestone_data}
    )
    self.assertEqual(response.status, "201 Created")
    self.assertEqual(response.content_type, "application/json")
    milestone = response.json["data"]
    self.assertEqual(milestone["type"], milestone_data["type"])
    self.assertIsNotNone(milestone["dateModified"])
    self.assertNotEqual(milestone["dateModified"], milestone_data["dateModified"])
    self.assertIsNone(milestone.get("dueDate"))
    contract = self.app.get(f"/agreements/{self.agreement_id}/contracts/{self.contract_id}").json["data"]
    self.assertEqual(contract["status"], MILESTONE_CONTRACT_STATUSES[milestone["type"]])


def post_disqualification_milestone_with_documents(self):
    milestone_data = deepcopy(disqualification_milestone_data_with_documents)
    milestone_data["documents"][0]["url"] = self.generate_docservice_url()
    milestone_data["dateModified"] = "2020-03-10T01:00:20.514000+02:00"
    milestone_data["dueDate"] = "2020-03-10T01:00:20.514000+02:00"
    response = self.app.post_json(
        f"/agreements/{self.agreement_id}/contracts/{self.contract_id}/milestones?acc_token={self.framework_token}",
        {"data": milestone_data}
    )
    self.assertEqual(response.status, "201 Created")
    self.assertEqual(response.content_type, "application/json")
    milestone = response.json["data"]
    self.assertEqual(milestone["type"], milestone_data["type"])
    self.assertIsNotNone(milestone["dateModified"])
    self.assertNotEqual(milestone["dateModified"], milestone_data["dateModified"])
    self.assertIsNone(milestone.get("dueDate"))
    self.assertEqual(len(milestone["documents"]), len(milestone_data["documents"]))
    contract = self.app.get(f"/agreements/{self.agreement_id}/contracts/{self.contract_id}").json["data"]
    self.assertEqual(contract["status"], MILESTONE_CONTRACT_STATUSES[milestone["type"]])


def get_documents_list(self):
    response = self.app.get(
        f"/agreements/{self.agreement_id}/contracts/{self.contract_id}/milestones/{self.milestone_id}/documents"
    )
    documents = response.json["data"]
    self.assertEqual(len(documents), len(self.initial_milestone_data["documents"]))


def get_document_by_id(self):
    documents = self.app.get(
            f"/agreements/{self.agreement_id}/contracts/{self.contract_id}/milestones/{self.milestone_id}"
        ).json["data"].get("documents")
    for doc in documents:
        response = self.app.get(
            f"/agreements/{self.agreement_id}/contracts/{self.contract_id}/milestones/{self.milestone_id}"
            f"/documents/{doc['id']}")
        document = response.json["data"]
        self.assertEqual(doc["id"], document["id"])
        self.assertEqual(doc["title"], document["title"])
        self.assertEqual(doc["format"], document["format"])
        self.assertEqual(doc["datePublished"], document["datePublished"])


def create_milestone_document_forbidden(self):
    # without acc_token
    response = self.app.post(
        f"/agreements/{self.agreement_id}/contracts/{self.contract_id}/milestones/{self.milestone_id}/documents",
        upload_files=[("file", "укр.doc", b"content")],
        status=403
    )
    self.assertEqual(response.status, "403 Forbidden")
    self.assertEqual(
        response.json["errors"],
        [{"description": "Forbidden", "location": "url", "name": "permission"}],
    )

    with change_auth(self.app, ("Basic", ("broker1", ""))):
        response = self.app.post(
            f"/agreements/{self.agreement_id}/contracts/{self.contract_id}/milestones/{self.milestone_id}"
            f"/documents?acc_token={self.framework_token}",
            upload_files=[("file", "укр.doc", b"content")],
            status=403
        )
        self.assertEqual(response.status, "403 Forbidden")
        self.assertEqual(
            response.json["errors"],
            [{"description": "Forbidden", "location": "url", "name": "permission"}],
        )


def create_milestone_documents(self):
    response = self.app.post(
        f"/agreements/{self.agreement_id}/contracts/{self.contract_id}/milestones/{self.milestone_id}"
        f"/documents?acc_token={self.framework_token}",
        upload_files=[("file", "укр.doc", b"content")],
    )
    self.assertEqual(response.status, "201 Created")
    self.assertEqual(response.content_type, "application/json")

    with change_auth(self.app, ("Basic", ("token", ""))):
        response = self.app.post(
            f"/agreements/{self.agreement_id}/contracts/{self.contract_id}/milestones/{self.milestone_id}"
            f"/documents?acc_token={self.framework_token}",
            upload_files=[("file", "укр.doc", b"content")],
        )
        self.assertEqual(response.status, "201 Created")


def create_milestone_document_json_bulk(self):
    response = self.app.post_json(
        f"/agreements/{self.agreement_id}/contracts/{self.contract_id}/milestones/{self.milestone_id}"
        f"/documents?acc_token={self.framework_token}",
        {
            "data": [
                {
                    "title": "name1.doc",
                    "url": self.generate_docservice_url(),
                    "hash": "md5:" + "0" * 32,
                    "format": "application/msword",
                },
                {
                    "title": "name2.doc",
                    "url": self.generate_docservice_url(),
                    "hash": "md5:" + "0" * 32,
                    "format": "application/msword",
                }
            ]
        },
    )
    self.assertEqual(response.status, "201 Created")
    self.assertEqual(response.content_type, "application/json")
    doc_1 = response.json["data"][0]
    doc_2 = response.json["data"][1]

    def assert_document(document, title):
        self.assertEqual(title, document["title"])
        self.assertIn("Signature=", document["url"])
        self.assertIn("KeyID=", document["url"])
        self.assertNotIn("Expires=", document["url"])

    assert_document(doc_1, "name1.doc")
    assert_document(doc_2, "name2.doc")

    milestone = self.app.get(
        f"/agreements/{self.agreement_id}/contracts/{self.contract_id}/milestones/{self.milestone_id}"
    ).json["data"]
    doc_1 = milestone["documents"][1]
    doc_2 = milestone["documents"][2]
    assert_document(doc_1, "name1.doc")
    assert_document(doc_2, "name2.doc")

    response = self.app.get(
        f"/agreements/{self.agreement_id}/contracts/{self.contract_id}/milestones/{self.milestone_id}/documents"
    )
    self.assertEqual(response.status, "200 OK")
    self.assertEqual(response.content_type, "application/json")
    doc_1 = response.json["data"][1]
    doc_2 = response.json["data"][2]
    assert_document(doc_1, "name1.doc")
    assert_document(doc_2, "name2.doc")


def put_milestone_document(self):
    response = self.app.post(
        f"/agreements/{self.agreement_id}/contracts/{self.contract_id}/milestones/{self.milestone_id}"
        f"/documents?acc_token={self.framework_token}",
        upload_files=[("file", "укр.doc", b"content")],
    )
    self.assertEqual(response.status, "201 Created")
    self.assertEqual(response.content_type, "application/json")
    self.assertEqual("укр.doc", response.json["data"]["title"])
    doc_id = response.json["data"]["id"]
    dateModified = response.json["data"]["dateModified"]
    self.assertIn(doc_id, response.headers["Location"])
    response = self.app.put(
        f"/agreements/{self.agreement_id}/contracts/{self.contract_id}/milestones/{self.milestone_id}"
        f"/documents/{doc_id}?acc_token={self.framework_token}",
        upload_files=[("file", "name name.doc", b"content2")],
    )
    self.assertEqual(response.status, "200 OK")
    self.assertEqual(response.content_type, "application/json")
    self.assertEqual(doc_id, response.json["data"]["id"])
    if self.docservice:
        self.assertIn("Signature=", response.json["data"]["url"])
        self.assertIn("KeyID=", response.json["data"]["url"])
        self.assertNotIn("Expires=", response.json["data"]["url"])
        key = response.json["data"]["url"].split("/")[-1].split("?")[0]
        milestone = self.app.get(
            f"/agreements/{self.agreement_id}/contracts/{self.contract_id}/milestones/{self.milestone_id}"
        ).json["data"]
        self.assertIn(key, milestone["documents"][-1]["url"])
        self.assertIn("Signature=", milestone["documents"][-1]["url"])
        self.assertIn("KeyID=", milestone["documents"][-1]["url"])
        self.assertNotIn("Expires=", milestone["documents"][-1]["url"])
    response = self.app.get(
        f"/agreements/{self.agreement_id}/contracts/{self.contract_id}/milestones/{self.milestone_id}"
        f"/documents/{doc_id}",
    )
    self.assertEqual(response.status, "200 OK")
    self.assertEqual(response.content_type, "application/json")
    self.assertEqual(doc_id, response.json["data"]["id"])
    self.assertEqual("name name.doc", response.json["data"]["title"])
    dateModified2 = response.json["data"]["dateModified"]
    self.assertTrue(dateModified < dateModified2)
    self.assertEqual(dateModified, response.json["data"]["previousVersions"][0]["dateModified"])

    response = self.app.get(
        f"/agreements/{self.agreement_id}/contracts/{self.contract_id}/milestones/{self.milestone_id}"
        f"/documents?all=true",
    )
    self.assertEqual(response.status, "200 OK")
    self.assertEqual(response.content_type, "application/json")
    self.assertEqual(dateModified, response.json["data"][1]["dateModified"])
    self.assertEqual(dateModified2, response.json["data"][2]["dateModified"])

    response = self.app.post(
        f"/agreements/{self.agreement_id}/contracts/{self.contract_id}/milestones/{self.milestone_id}"
        f"/documents?acc_token={self.framework_token}",
        upload_files=[("file", "name.doc", b"content")],
    )
    self.assertEqual(response.status, "201 Created")
    self.assertEqual(response.content_type, "application/json")
    doc_id = response.json["data"]["id"]
    dateModified = response.json["data"]["dateModified"]
    self.assertIn(doc_id, response.headers["Location"])

    response = self.app.get(
        f"/agreements/{self.agreement_id}/contracts/{self.contract_id}/milestones/{self.milestone_id}/documents",
    )
    self.assertEqual(response.status, "200 OK")
    self.assertEqual(response.content_type, "application/json")
    self.assertEqual(dateModified2, response.json["data"][1]["dateModified"])
    self.assertEqual(dateModified, response.json["data"][2]["dateModified"])
    response = self.app.put(
        f"/agreements/{self.agreement_id}/contracts/{self.contract_id}/milestones/{self.milestone_id}"
        f"/documents/{doc_id}?acc_token={self.framework_token}",
        status=404,
        upload_files=[("invalid_name", "name.doc", b"content")],
    )
    self.assertEqual(response.status, "404 Not Found")
    self.assertEqual(response.content_type, "application/json")
    self.assertEqual(response.json["status"], "error")
    self.assertEqual(response.json["errors"], [{"description": "Not Found", "location": "body", "name": "file"}])
    response = self.app.put(
        f"/agreements/{self.agreement_id}/contracts/{self.contract_id}/milestones/{self.milestone_id}"
        f"/documents/{doc_id}?acc_token={self.framework_token}",
        "content3",
        content_type="application/msword",
    )
    self.assertEqual(response.status, "200 OK")
    self.assertEqual(response.content_type, "application/json")
    self.assertEqual(doc_id, response.json["data"]["id"])
    if self.docservice:
        self.assertIn("Signature=", response.json["data"]["url"])
        self.assertIn("KeyID=", response.json["data"]["url"])
        self.assertNotIn("Expires=", response.json["data"]["url"])
        key = response.json["data"]["url"].split("/")[-1].split("?")[0]
        milestone = self.app.get(
            f"/agreements/{self.agreement_id}/contracts/{self.contract_id}/milestones/{self.milestone_id}"
        ).json["data"]
        self.assertIn(key, milestone["documents"][-1]["url"])
        self.assertIn("Signature=", milestone["documents"][-1]["url"])
        self.assertIn("KeyID=", milestone["documents"][-1]["url"])
        self.assertNotIn("Expires=", milestone["documents"][-1]["url"])
    else:
        key = response.json["data"]["url"].split("?")[-1].split("=")[-1]
    if self.docservice:
        response = self.app.get(
            f"/agreements/{self.agreement_id}/contracts/{self.contract_id}/milestones/{self.milestone_id}"
            f"/documents/{doc_id}?download={key}"
        )
        self.assertEqual(response.status, "302 Moved Temporarily")
        self.assertEqual(response.content_type, "application/json")

    response = self.app.get(
        f"/agreements/{self.agreement_id}/contracts/{self.contract_id}/milestones/{self.milestone_id}/documents"
    )
    self.assertEqual(response.status, "200 OK")
    doc_id = response.json["data"][0]["id"]

    response = self.app.patch_json(
        f"/agreements/{self.agreement_id}/contracts/{self.contract_id}/milestones/{self.milestone_id}"
        f"/documents/{doc_id}?acc_token={self.framework_token}",
        {"data": {"documentType": None}},
    )
    self.assertEqual(response.status, "200 OK")
    self.assertEqual(response.content_type, "application/json")

    self.set_contract_status("terminated")
    response = self.app.put(
        f"/agreements/{self.agreement_id}/contracts/{self.contract_id}/milestones/{self.milestone_id}"
        f"/documents/{doc_id}?acc_token={self.framework_token}",
        "contentX",
        content_type="application/msword",
        status=403,
    )
    self.assertEqual(response.status, "403 Forbidden")
    self.assertEqual(
        response.json["errors"],
        [
            {
                "description": "Can't update document in current (terminated) contract status",
                "location": "body",
                "name": "data",
            }
        ],
    )
    #  document in current (complete) contract status
    response = self.app.patch_json(
        f"/agreements/{self.agreement_id}/contracts/{self.contract_id}/milestones/{self.milestone_id}"
        f"/documents/{doc_id}?acc_token={self.framework_token}",
        {"data": {"documentType": None}},
        status=403,
    )
    self.assertEqual(response.status, "403 Forbidden")
    self.assertEqual(
        response.json["errors"],
        [
            {
                "description": "Can't update document in current (terminated) contract status",
                "location": "body",
                "name": "data",
            }
        ],
    )
