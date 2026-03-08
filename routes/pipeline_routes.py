from flask import Blueprint, request, jsonify
from models import AnalyzedProfile
from services.gap_analysis import screen_candidate_fit, build_candidate_profile

pipeline_bp = Blueprint("pipeline", __name__)


@pipeline_bp.route("/gap-analysis", methods=["POST"])
def gap_analysis():

    data = request.json

    profile_id = data.get("profile_id")
    jd = data.get("jd")

    if not profile_id or not jd:
        return jsonify({"error": "profile_id and jd required"}), 400

    profile = AnalyzedProfile.query.get(profile_id)

    if not profile:
        return jsonify({"error": "Profile not found"}), 404

    candidate_profile = build_candidate_profile(profile)

    result = screen_candidate_fit(candidate_profile, jd)

    return jsonify(result)