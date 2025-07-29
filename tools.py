"""
Tools module for Pokemon bot functionality.
Contains tool definitions and implementations for function calling.
"""

import json
from typing import Dict, Any, Optional
from datetime import datetime, timedelta


# Hardcoded Pokemon health records for testing
POKEMON_HEALTH_RECORDS = {
    "001": {
        "pokemon_id": "001",
        "name": "Pikachu",
        "species": "Electric Mouse Pokemon",
        "trainer": "Ash Ketchum",
        "level": 25,
        "health_status": "Excellent",
        "current_hp": 85,
        "max_hp": 85,
        "last_checkup": "2024-01-15",
        "next_checkup_due": "2024-04-15",
        "vaccinations": {
            "pokerus_vaccine": "2024-01-10",
            "paralysis_preventive": "2023-12-05",
            "status_immunity": "2024-01-10"
        },
        "recent_battles": 3,
        "injuries": [],
        "medications": [],
        "diet": "Standard Electric-type nutrition, extra protein",
        "exercise_level": "High - daily training",
        "mood": "Energetic and happy",
        "notes": "Very healthy specimen. Shows excellent battle readiness. No concerns."
    },
    "002": {
        "pokemon_id": "002",
        "name": "Slowpoke", 
        "species": "Dopey Pokemon",
        "trainer": "Professor Oak",
        "level": 18,
        "health_status": "Good",
        "current_hp": 95,
        "max_hp": 95,
        "last_checkup": "2024-01-10",
        "next_checkup_due": "2024-04-10",
        "vaccinations": {
            "pokerus_vaccine": "2023-11-15",
            "confusion_preventive": "2024-01-05",
            "water_immunity": "2023-12-20"
        },
        "recent_battles": 0,
        "injuries": [],
        "medications": ["Mild stimulant for alertness"],
        "diet": "High-energy fish, mental stimulation treats",
        "exercise_level": "Low - prefers lounging",
        "mood": "Calm and content",
        "notes": "Normal for species. Reaction time slower than average but this is typical. No health issues."
    },
    "003": {
        "pokemon_id": "003",
        "name": "Psyduck",
        "species": "Duck Pokemon", 
        "trainer": "Misty",
        "level": 22,
        "health_status": "Concerning",
        "current_hp": 68,
        "max_hp": 75,
        "last_checkup": "2024-01-12",
        "next_checkup_due": "2024-02-12",
        "vaccinations": {
            "pokerus_vaccine": "2024-01-01",
            "psychic_stabilizer": "2024-01-12",
            "headache_preventive": "2024-01-12"
        },
        "recent_battles": 1,
        "injuries": ["Chronic headaches", "Psychic power instability"],
        "medications": ["Psychic suppressant", "Pain reliever", "Concentration enhancer"],
        "diet": "Specialized brain-food diet, omega-3 supplements",
        "exercise_level": "Moderate - limited due to headaches",
        "mood": "Confused and occasionally distressed",
        "notes": "Requires ongoing monitoring. Psychic powers cause frequent headaches. May need specialist consultation."
    },
    "004": {
        "pokemon_id": "004",
        "name": "Magikarp",
        "species": "Fish Pokemon",
        "trainer": "Team Rocket Grunt",
        "level": 12,
        "health_status": "Poor",
        "current_hp": 15,
        "max_hp": 20,
        "last_checkup": "2024-01-08",
        "next_checkup_due": "2024-01-22",
        "vaccinations": {
            "pokerus_vaccine": "2023-10-15",
            "water_immunity": "2023-11-20"
        },
        "recent_battles": 5,
        "injuries": ["Scale damage", "Fin tears", "General exhaustion"],
        "medications": ["Healing potion", "Vitality booster", "Scale repair cream"],
        "diet": "Recovery diet with extra vitamins",
        "exercise_level": "Very low - rest prescribed",
        "mood": "Dejected and weak",
        "notes": "URGENT: Overworked and undernourished. Needs immediate rest and care. Consider trainer intervention."
    },
    "005": {
        "pokemon_id": "005",
        "name": "Snorlax",
        "species": "Sleeping Pokemon",
        "trainer": "Wild Pokemon",
        "level": 35,
        "health_status": "Excellent",
        "current_hp": 465,
        "max_hp": 465,
        "last_checkup": "2024-01-05",
        "next_checkup_due": "2024-07-05",
        "vaccinations": {
            "pokerus_vaccine": "2023-12-01",
            "sleep_disorder_preventive": "2024-01-05"
        },
        "recent_battles": 0,
        "injuries": [],
        "medications": [],
        "diet": "Massive quantities of berries and natural foods",
        "exercise_level": "Minimal - sleeps 20+ hours daily",
        "mood": "Peaceful and well-rested",
        "notes": "Perfect health for species. Excellent weight and vital signs. No concerns - sleeping pattern is normal."
    }
}


def pokemon_health_check(pokemon_id: str) -> str:
    """
    Retrieve health record for a Pokemon by ID.
    
    Args:
        pokemon_id: The string ID of the Pokemon (e.g., "001", "002")
        
    Returns:
        JSON string containing the health record or error message
    """
    try:
        # Clean and validate the ID
        pokemon_id = pokemon_id.strip().zfill(3)  # Pad with zeros if needed
        
        if pokemon_id in POKEMON_HEALTH_RECORDS:
            record = POKEMON_HEALTH_RECORDS[pokemon_id]
            
            # Add some computed fields for convenience
            health_summary = {
                **record,
                "health_percentage": round((record["current_hp"] / record["max_hp"]) * 100, 1),
                "checkup_overdue": _is_checkup_overdue(record["next_checkup_due"]),
                "vaccination_status": _check_vaccination_status(record["vaccinations"]),
                "overall_assessment": _get_overall_assessment(record)
            }
            
            return json.dumps({
                "status": "success",
                "data": health_summary
            }, indent=2)
        else:
            available_ids = list(POKEMON_HEALTH_RECORDS.keys())
            return json.dumps({
                "status": "not_found",
                "message": f"No health record found for Pokemon ID '{pokemon_id}'",
                "available_ids": available_ids
            }, indent=2)
            
    except Exception as e:
        return json.dumps({
            "status": "error",
            "message": f"Error retrieving health record: {str(e)}"
        }, indent=2)


def _is_checkup_overdue(next_checkup_str: str) -> bool:
    """Check if a checkup is overdue."""
    try:
        next_checkup = datetime.strptime(next_checkup_str, "%Y-%m-%d")
        return datetime.now() > next_checkup
    except:
        return False


def _check_vaccination_status(vaccinations: Dict[str, str]) -> str:
    """Check vaccination status and return assessment."""
    try:
        now = datetime.now()
        outdated_vaccines = []
        
        for vaccine, date_str in vaccinations.items():
            vaccine_date = datetime.strptime(date_str, "%Y-%m-%d")
            # Consider vaccines outdated if older than 6 months
            if now - vaccine_date > timedelta(days=180):
                outdated_vaccines.append(vaccine)
        
        if not outdated_vaccines:
            return "All vaccinations current"
        elif len(outdated_vaccines) == len(vaccinations):
            return "All vaccinations outdated"
        else:
            return f"Some vaccinations outdated: {', '.join(outdated_vaccines)}"
    except:
        return "Vaccination status unclear"


def _get_overall_assessment(record: Dict[str, Any]) -> str:
    """Generate an overall health assessment."""
    health_status = record["health_status"].lower()
    hp_percentage = (record["current_hp"] / record["max_hp"]) * 100
    has_injuries = len(record["injuries"]) > 0
    on_medications = len(record["medications"]) > 0
    
    if health_status == "excellent" and hp_percentage >= 90 and not has_injuries:
        return "Excellent condition - no concerns"
    elif health_status == "good" and hp_percentage >= 75:
        return "Good condition - minor monitoring needed" if on_medications else "Good condition"
    elif health_status == "concerning" or hp_percentage < 75:
        return "Needs attention - schedule follow-up soon"
    elif health_status == "poor" or hp_percentage < 50:
        return "URGENT - requires immediate care"
    else:
        return "Status requires evaluation"


# Self-sufficient tool registry containing both function implementations and OpenAI tool definitions
TOOL_REGISTRY = {
    "pokemon_health_check": {
        "function": pokemon_health_check,
        "definition": {
            "type": "function",
            "function": {
                "name": "pokemon_health_check",
                "description": "Look up detailed health record for a Pokemon using its ID number. Returns comprehensive health information including current status, medical history, and care recommendations.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "pokemon_id": {
                            "type": "string",
                            "description": "The ID of the Pokemon to look up (e.g., '001', '002', '1'). Will be automatically padded with zeros if needed."
                        }
                    },
                    "required": ["pokemon_id"]
                }
            }
        }
    }
}


# Export everything needed
__all__ = [
    "pokemon_health_check",
    "TOOL_REGISTRY",
    "POKEMON_HEALTH_RECORDS"
] 