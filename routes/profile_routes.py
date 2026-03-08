from flask import Blueprint, jsonify
from models import AnalyzedProfile

profile_bp = Blueprint("profiles", __name__)


@profile_bp.route("/analyzed", methods=["GET"])
def get_analyzed_profiles():

    profiles = AnalyzedProfile.query.order_by(
        AnalyzedProfile.created_at.desc()
    ).all()

    result = []

    for p in profiles:

        result.append({
            "id": p.id,
            "name": p.name,
            "headline": p.headline,
            "profile_url": p.profile_url,
            "skills": p.skills,
            
        })

    return jsonify(result)