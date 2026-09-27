from flask import Flask, render_template, request, jsonify
import requests

app = Flask(__name__)

API_URL = "https://clinicaltrials.gov/api/v2/studies"


def get_studies(cancer="cancer"):
    params = {
        "query.cond": cancer,
        "filter.advanced": "AREA[LocationCountry]Greece",
        "filter.overallStatus": "RECRUITING|NOT_YET_RECRUITING",
        "pageSize": 100,
        "format": "json"
    }

    response = requests.get(API_URL, params=params, timeout=30)
    response.raise_for_status()

    return response.json().get("studies", [])


def process_study(study):
    protocol = study.get("protocolSection", {})

    identification = protocol.get("identificationModule", {})
    status = protocol.get("statusModule", {})
    design = protocol.get("designModule", {})

    sponsor = protocol.get(
        "sponsorCollaboratorsModule", {}
    ).get("leadSponsor", {})

    locations = protocol.get(
        "contactsLocationsModule", {}
    ).get("locations", [])

    greek_locations = []

    for location in locations:
        if location.get("country", "").lower() == "greece":
            greek_locations.append({
                "facility": location.get("facility", ""),
                "city": location.get("city", ""),
                "state": location.get("state", ""),
                "zip": location.get("zip", "")
            })

    return {
        "nct": identification.get("nctId", ""),
        "title": identification.get("briefTitle", ""),
        "status": status.get("overallStatus", ""),
        "phase": ", ".join(design.get("phases", [])),
        "sponsor": sponsor.get("name", ""),
        "locations": greek_locations,
        "url": "https://clinicaltrials.gov/study/"
               + identification.get("nctId", "")
    }


@app.route("/")
def home():
    return render_template("index.html")


@app.route("/api/trials")
def trials():

    cancer = request.args.get("cancer", "cancer")
    city = request.args.get("city", "all")
    hospital = request.args.get("hospital", "all")

    try:
        raw_studies = get_studies(cancer)
        studies = []

        for study in raw_studies:

            processed = process_study(study)
            filtered_locations = []

            for location in processed["locations"]:

                location_city = location["city"] or ""
                location_hospital = location["facility"] or ""

                city_match = (
                    city == "all"
                    or city.lower() in location_city.lower()
                )

                hospital_match = (
                    hospital == "all"
                    or hospital.lower() in location_hospital.lower()
                )

                if city_match and hospital_match:
                    filtered_locations.append(location)

            if filtered_locations:
                processed["locations"] = filtered_locations
                studies.append(processed)

        return jsonify({
            "count": len(studies),
            "studies": studies
        })

    except Exception as error:
        return jsonify({
            "error": str(error)
        }), 500


@app.route("/api/hospitals")
def hospitals():

    cancer = request.args.get("cancer", "cancer")
    city = request.args.get("city", "all")

    try:

        raw_studies = get_studies(cancer)
        hospitals = set()

        for study in raw_studies:

            processed = process_study(study)

            for location in processed["locations"]:

                facility = location["facility"] or ""
                location_city = location["city"] or ""

                if not facility:
                    continue

                if (
                    city == "all"
                    or city.lower() in location_city.lower()
                ):
                    hospitals.add(facility)

        return jsonify({
            "hospitals": sorted(hospitals)
        })

    except Exception as error:

        return jsonify({
            "error": str(error)
        }), 500


if __name__ == "__main__":
    app.run(
        host="127.0.0.1",
        port=5001,
        debug=True
    )
