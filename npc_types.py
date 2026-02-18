#!/usr/bin/env python3
"""
NPC Type System for Introvert Social RPG
Adds role-based templates, personality archetypes, and contextual behaviors
"""

from enum import Enum
from dataclasses import dataclass, field
from typing import Dict, List, Optional
import random

# ============================================================================
# ENUMS FOR NPC TYPES
# ============================================================================

class NPCRole(Enum):
    """Role-based NPC templates"""
    SERVICE_WORKER = "service_worker"      # Barista, cashier, bartender
    PROFESSIONAL = "professional"          # Coworker, client, networking contact
    SOCIAL = "social"                      # Bar/party attendee, event goer
    STRANGER = "stranger"                  # Random street/transit encounter
    LEISURE = "leisure"                    # Coffee shop browser, park visitor
    NEIGHBOR = "neighbor"                  # Lives nearby, shared space
    REGULAR = "regular"                    # See them often but never talk

class PersonalityArchetype(Enum):
    """Behavioral personality types"""
    EXTROVERT = "extrovert"               # High energy, talkative
    INTROVERT = "introvert"               # Quiet, appreciates brevity
    SKEPTIC = "skeptic"                   # Low initial trust, critical
    ENTHUSIAST = "enthusiast"             # Gets excited about interests
    BALANCED = "balanced"                 # Average on all dimensions

class SocialContext(Enum):
    """Why the NPC is at this location"""
    TASK_FOCUSED = "task_focused"         # Here to accomplish something
    LEISURE = "leisure"                    # Relaxing, open to chat
    TRAPPED = "trapped"                    # Waiting, might be bored
    WORKING = "working"                    # On the job
    SOCIALIZING = "socializing"           # Explicitly here to meet people

# ============================================================================
# NPC TYPE MODIFIERS
# ============================================================================

@dataclass
class NPCTypeModifiers:
    """Modifiers applied based on NPC type"""
    
    # Starting values
    base_receptiveness: float = 2.0
    base_bond: float = 0.0
    
    # Behavioral modifiers
    conversation_patience: float = 1.0     # Multiplier for tolerance
    time_pressure: bool = False            # Has external time constraints
    domain_boost: float = 0.0              # Extra boost for shared interests
    
    # Battery impact
    battery_drain_multiplier: float = 1.0  # Affects player's battery drain
    
    # Special traits
    carries_conversation: bool = False     # NPC contributes more
    comfortable_silence: bool = False      # Appreciates brevity
    critical_of_flirting: bool = False    # Higher flirt standards
    enthusiastic_about_interests: bool = False  # Gets very excited
    
    # Exit behavior
    failure_tolerance_modifier: int = 0    # +/- to base failure tolerance
    exits_gracefully: bool = True          # How they leave

# ============================================================================
# TYPE DEFINITIONS
# ============================================================================

class NPCTypeSystem:
    """Manages NPC type behaviors and modifiers"""
    
    @staticmethod
    def get_role_modifiers(role: NPCRole) -> NPCTypeModifiers:
        """Get modifiers for a specific role"""
        
        modifiers_map = {
            NPCRole.SERVICE_WORKER: NPCTypeModifiers(
                base_receptiveness=1.5,      # Lower - they're working
                conversation_patience=0.7,    # Less patient
                time_pressure=True,           # Customers waiting
                battery_drain_multiplier=1.2, # Slightly more draining
                failure_tolerance_modifier=-1, # Less tolerant of mistakes
                exits_gracefully=True
            ),
            
            NPCRole.PROFESSIONAL: NPCTypeModifiers(
                base_receptiveness=2.0,
                conversation_patience=1.0,
                domain_boost=0.2,             # +20% when topics match profession
                battery_drain_multiplier=1.1,
                failure_tolerance_modifier=0,
                exits_gracefully=True
            ),
            
            NPCRole.SOCIAL: NPCTypeModifiers(
                base_receptiveness=2.5,       # Higher - here to socialize
                conversation_patience=1.2,    # More patient
                time_pressure=False,
                battery_drain_multiplier=1.3, # More draining (high energy)
                failure_tolerance_modifier=1, # More forgiving
                exits_gracefully=True
            ),
            
            NPCRole.STRANGER: NPCTypeModifiers(
                base_receptiveness=1.0,       # Very low - why are you talking to me?
                conversation_patience=0.6,    # Not patient
                time_pressure=True,           # Wants to get where they're going
                battery_drain_multiplier=1.4, # Very draining (awkward)
                failure_tolerance_modifier=-1,
                exits_gracefully=False        # Might just walk away
            ),
            
            NPCRole.LEISURE: NPCTypeModifiers(
                base_receptiveness=2.2,
                conversation_patience=1.1,
                time_pressure=False,
                battery_drain_multiplier=0.9, # Less draining (relaxed vibe)
                failure_tolerance_modifier=1,
                exits_gracefully=True
            ),
            
            NPCRole.NEIGHBOR: NPCTypeModifiers(
                base_receptiveness=2.0,
                base_bond=0.25,               # Already familiar
                conversation_patience=1.0,
                time_pressure=False,
                battery_drain_multiplier=0.9,
                failure_tolerance_modifier=1, # More forgiving (see each other again)
                exits_gracefully=True
            ),
            
            NPCRole.REGULAR: NPCTypeModifiers(
                base_receptiveness=1.8,
                base_bond=0.5,                # Recognize each other
                conversation_patience=0.9,
                time_pressure=False,
                battery_drain_multiplier=1.0,
                failure_tolerance_modifier=0,
                exits_gracefully=True
            )
        }
        
        return modifiers_map.get(role, NPCTypeModifiers())
    
    @staticmethod
    def get_archetype_modifiers(archetype: PersonalityArchetype) -> NPCTypeModifiers:
        """Get modifiers for personality archetype"""
        
        modifiers_map = {
            PersonalityArchetype.EXTROVERT: NPCTypeModifiers(
                base_receptiveness=2.5,
                conversation_patience=1.3,    # Very patient
                carries_conversation=True,    # Talks more
                battery_drain_multiplier=1.4, # Exhausting
                failure_tolerance_modifier=2, # Very forgiving
                exits_gracefully=True
            ),
            
            PersonalityArchetype.INTROVERT: NPCTypeModifiers(
                base_receptiveness=1.8,
                conversation_patience=1.0,
                comfortable_silence=True,     # Appreciates brevity
                battery_drain_multiplier=0.7, # Less draining
                failure_tolerance_modifier=0,
                exits_gracefully=True
            ),
            
            PersonalityArchetype.SKEPTIC: NPCTypeModifiers(
                base_receptiveness=1.3,       # Low initial trust
                conversation_patience=0.8,
                critical_of_flirting=True,    # 30% penalty to flirt success
                battery_drain_multiplier=1.2,
                failure_tolerance_modifier=-1,
                exits_gracefully=False        # Might be blunt
            ),
            
            PersonalityArchetype.ENTHUSIAST: NPCTypeModifiers(
                base_receptiveness=2.3,
                conversation_patience=1.2,
                domain_boost=0.3,             # +30% for shared interests
                enthusiastic_about_interests=True,
                battery_drain_multiplier=1.3,
                failure_tolerance_modifier=1,
                exits_gracefully=True
            ),
            
            PersonalityArchetype.BALANCED: NPCTypeModifiers(
                base_receptiveness=2.0,
                conversation_patience=1.0,
                battery_drain_multiplier=1.0,
                failure_tolerance_modifier=0,
                exits_gracefully=True
            )
        }
        
        return modifiers_map.get(archetype, NPCTypeModifiers())
    
    @staticmethod
    def get_context_modifiers(context: SocialContext) -> NPCTypeModifiers:
        """Get modifiers for social context"""
        
        modifiers_map = {
            SocialContext.TASK_FOCUSED: NPCTypeModifiers(
                base_receptiveness=1.7,
                conversation_patience=0.8,
                time_pressure=True,
                battery_drain_multiplier=1.1,
                failure_tolerance_modifier=-1,
                exits_gracefully=True
            ),
            
            SocialContext.LEISURE: NPCTypeModifiers(
                base_receptiveness=2.3,
                conversation_patience=1.2,
                time_pressure=False,
                battery_drain_multiplier=0.9,
                failure_tolerance_modifier=1,
                exits_gracefully=True
            ),
            
            SocialContext.TRAPPED: NPCTypeModifiers(
                # Roll determines if bored (receptive) or frustrated (not)
                base_receptiveness=random.choice([1.5, 2.5]),
                conversation_patience=random.choice([0.7, 1.1]),
                time_pressure=False,
                battery_drain_multiplier=1.0,
                failure_tolerance_modifier=random.choice([-1, 1]),
                exits_gracefully=True
            ),
            
            SocialContext.WORKING: NPCTypeModifiers(
                base_receptiveness=1.5,
                conversation_patience=0.7,
                time_pressure=True,
                battery_drain_multiplier=1.2,
                failure_tolerance_modifier=-1,
                exits_gracefully=True
            ),
            
            SocialContext.SOCIALIZING: NPCTypeModifiers(
                base_receptiveness=2.5,
                conversation_patience=1.3,
                time_pressure=False,
                battery_drain_multiplier=1.2,
                failure_tolerance_modifier=2,
                exits_gracefully=True
            )
        }
        
        return modifiers_map.get(context, NPCTypeModifiers())
    
    @staticmethod
    def combine_modifiers(role_mods: NPCTypeModifiers,
                         archetype_mods: NPCTypeModifiers,
                         context_mods: NPCTypeModifiers) -> NPCTypeModifiers:
        """Combine multiple modifier sets intelligently"""
        
        combined = NPCTypeModifiers()
        
        # Receptiveness: average of all three
        combined.base_receptiveness = (
            role_mods.base_receptiveness +
            archetype_mods.base_receptiveness +
            context_mods.base_receptiveness
        ) / 3.0
        
        # Bond: use highest
        combined.base_bond = max(
            role_mods.base_bond,
            archetype_mods.base_bond,
            context_mods.base_bond
        )
        
        # Patience: multiply all
        combined.conversation_patience = (
            role_mods.conversation_patience *
            archetype_mods.conversation_patience *
            context_mods.conversation_patience
        )
        
        # Time pressure: any TRUE makes it TRUE
        combined.time_pressure = (
            role_mods.time_pressure or
            archetype_mods.time_pressure or
            context_mods.time_pressure
        )
        
        # Domain boost: sum all
        combined.domain_boost = (
            role_mods.domain_boost +
            archetype_mods.domain_boost +
            context_mods.domain_boost
        )
        
        # Battery multiplier: multiply all
        combined.battery_drain_multiplier = (
            role_mods.battery_drain_multiplier *
            archetype_mods.battery_drain_multiplier *
            context_mods.battery_drain_multiplier
        )
        
        # Special traits: any TRUE makes it TRUE
        combined.carries_conversation = (
            role_mods.carries_conversation or
            archetype_mods.carries_conversation
        )
        
        combined.comfortable_silence = (
            role_mods.comfortable_silence or
            archetype_mods.comfortable_silence
        )
        
        combined.critical_of_flirting = (
            role_mods.critical_of_flirting or
            archetype_mods.critical_of_flirting
        )
        
        combined.enthusiastic_about_interests = (
            role_mods.enthusiastic_about_interests or
            archetype_mods.enthusiastic_about_interests
        )
        
        # Failure tolerance: sum all modifiers
        combined.failure_tolerance_modifier = (
            role_mods.failure_tolerance_modifier +
            archetype_mods.failure_tolerance_modifier +
            context_mods.failure_tolerance_modifier
        )
        
        # Exits gracefully: all must be TRUE
        combined.exits_gracefully = (
            role_mods.exits_gracefully and
            archetype_mods.exits_gracefully and
            context_mods.exits_gracefully
        )
        
        return combined
    
    @staticmethod
    def apply_modifiers_to_npc(npc_state, modifiers: NPCTypeModifiers):
        """Apply modifiers to an NPC state object"""
        
        # Apply base values
        npc_state.receptiveness = modifiers.base_receptiveness
        npc_state.bond = modifiers.base_bond
        
        # Store modifiers for later use
        npc_state.type_modifiers = modifiers
        
        return npc_state
    
    @staticmethod
    def adjust_failure_tolerance(base_tolerance: int, modifiers: NPCTypeModifiers) -> int:
        """Adjust failure tolerance based on type"""
        return max(0, base_tolerance + modifiers.failure_tolerance_modifier)
    
    @staticmethod
    def adjust_battery_drain(base_drain: int, modifiers: NPCTypeModifiers) -> int:
        """Adjust battery drain based on type"""
        return int(base_drain * modifiers.battery_drain_multiplier)
    
    @staticmethod
    def adjust_flirt_success(base_rate: int, modifiers: NPCTypeModifiers) -> int:
        """Adjust flirt success rate based on type"""
        if modifiers.critical_of_flirting:
            return int(base_rate * 0.7)  # 30% penalty
        return base_rate
    
    @staticmethod
    def get_time_pressure_dialogue(role: NPCRole, context: SocialContext) -> Optional[str]:
        """Generate time pressure flavor text"""
        
        if not (NPCTypeSystem.get_role_modifiers(role).time_pressure or
                NPCTypeSystem.get_context_modifiers(context).time_pressure):
            return None
        
        time_pressure_lines = {
            NPCRole.SERVICE_WORKER: [
                "glances at the line forming behind you",
                "looks toward the other customers waiting",
                "checks the order screen briefly"
            ],
            NPCRole.STRANGER: [
                "checks their phone",
                "glances down the street",
                "shifts their weight, ready to move"
            ],
            SocialContext.TASK_FOCUSED: [
                "glances at their shopping list",
                "checks their watch",
                "looks toward their destination"
            ],
            SocialContext.WORKING: [
                "glances at their workstation",
                "checks the time",
                "looks around at other tasks"
            ]
        }
        
        # Get applicable lines
        applicable = []
        if role in time_pressure_lines:
            applicable.extend(time_pressure_lines[role])
        if context in time_pressure_lines:
            applicable.extend(time_pressure_lines[context])
        
        return random.choice(applicable) if applicable else "seems a bit busy"

# ============================================================================
# GENERATION HELPERS
# ============================================================================

class NPCTypeGenerator:
    """Helper for generating typed NPCs"""
    
    @staticmethod
    def generate_prompt_additions(role: NPCRole, 
                                  archetype: PersonalityArchetype,
                                  context: SocialContext) -> str:
        """Generate additional context for Claude's NPC generation"""
        
        role_descriptions = {
            NPCRole.SERVICE_WORKER: "They're working (barista/cashier/bartender) and somewhat busy with their job.",
            NPCRole.PROFESSIONAL: "They're in a professional context (coworker/client/networking). Professional demeanor.",
            NPCRole.SOCIAL: "They're at a social venue (bar/party/event) and open to meeting people.",
            NPCRole.STRANGER: "They're a random stranger you're approaching. Slightly guarded.",
            NPCRole.LEISURE: "They're relaxing (coffee shop/park) with time to chat.",
            NPCRole.NEIGHBOR: "They're your neighbor. You've seen each other around but never really talked.",
            NPCRole.REGULAR: "You see this person regularly (same gym/coffee shop) but have never spoken."
        }
        
        archetype_descriptions = {
            PersonalityArchetype.EXTROVERT: "Personality: Outgoing, talkative, high energy. Enjoys conversation.",
            PersonalityArchetype.INTROVERT: "Personality: Quiet, thoughtful, values brevity. More reserved.",
            PersonalityArchetype.SKEPTIC: "Personality: Somewhat skeptical, takes time to warm up. Not easily impressed.",
            PersonalityArchetype.ENTHUSIAST: "Personality: Gets excited about their interests. Passionate and animated.",
            PersonalityArchetype.BALANCED: "Personality: Balanced temperament. Neither extremely outgoing nor reserved."
        }
        
        context_descriptions = {
            SocialContext.TASK_FOCUSED: "They're here to accomplish something specific and somewhat focused on that.",
            SocialContext.LEISURE: "They're here to relax and have time for conversation.",
            SocialContext.TRAPPED: "They're waiting (line/bus/appointment) and might be bored or frustrated.",
            SocialContext.WORKING: "They're at work and have job responsibilities to balance.",
            SocialContext.SOCIALIZING: "They're explicitly here to socialize and meet people."
        }
        
        additions = []
        additions.append(role_descriptions.get(role, ""))
        additions.append(archetype_descriptions.get(archetype, ""))
        additions.append(context_descriptions.get(context, ""))
        
        return " ".join(filter(None, additions))
    
    @staticmethod
    def suggest_role_from_location(location: str) -> NPCRole:
        """Suggest appropriate role based on location"""
        
        location_lower = location.lower()
        
        if any(word in location_lower for word in ['coffee shop', 'café', 'cafe', 'counter']):
            return random.choice([NPCRole.SERVICE_WORKER, NPCRole.LEISURE])
        
        if any(word in location_lower for word in ['bar', 'club', 'party', 'event']):
            return NPCRole.SOCIAL
        
        if any(word in location_lower for word in ['office', 'work', 'meeting', 'conference']):
            return NPCRole.PROFESSIONAL
        
        if any(word in location_lower for word in ['street', 'sidewalk', 'bus', 'train', 'transit']):
            return NPCRole.STRANGER
        
        if any(word in location_lower for word in ['park', 'library', 'bookstore']):
            return NPCRole.LEISURE
        
        if any(word in location_lower for word in ['building', 'apartment', 'hallway', 'mailroom']):
            return NPCRole.NEIGHBOR
        
        if any(word in location_lower for word in ['gym', 'studio', 'regular']):
            return NPCRole.REGULAR
        
        # Default
        return random.choice([NPCRole.LEISURE, NPCRole.STRANGER])
    
    @staticmethod
    def random_archetype() -> PersonalityArchetype:
        """Generate random personality archetype with weighted distribution"""
        
        weights = {
            PersonalityArchetype.BALANCED: 0.4,      # 40% - most common
            PersonalityArchetype.INTROVERT: 0.2,     # 20%
            PersonalityArchetype.EXTROVERT: 0.2,     # 20%
            PersonalityArchetype.ENTHUSIAST: 0.1,    # 10%
            PersonalityArchetype.SKEPTIC: 0.1        # 10%
        }
        
        archetypes = list(weights.keys())
        probabilities = list(weights.values())
        
        return random.choices(archetypes, weights=probabilities)[0]
    
    @staticmethod
    def suggest_context_from_location(location: str) -> SocialContext:
        """Suggest appropriate social context from location"""
        
        location_lower = location.lower()
        
        if any(word in location_lower for word in ['work', 'office', 'counter', 'register']):
            return SocialContext.WORKING
        
        if any(word in location_lower for word in ['line', 'queue', 'waiting', 'bus', 'dmv']):
            return SocialContext.TRAPPED
        
        if any(word in location_lower for word in ['party', 'bar', 'club', 'event', 'mixer']):
            return SocialContext.SOCIALIZING
        
        if any(word in location_lower for word in ['shopping', 'store', 'buying', 'errand']):
            return SocialContext.TASK_FOCUSED
        
        # Default leisure
        return SocialContext.LEISURE

# ============================================================================
# USAGE EXAMPLES
# ============================================================================

def example_usage():
    """Demonstrate NPC type system usage"""
    
    # Example 1: Coffee shop barista
    print("=== Example 1: Coffee Shop Barista ===")
    role = NPCRole.SERVICE_WORKER
    archetype = PersonalityArchetype.INTROVERT
    context = SocialContext.WORKING
    
    role_mods = NPCTypeSystem.get_role_modifiers(role)
    arch_mods = NPCTypeSystem.get_archetype_modifiers(archetype)
    ctx_mods = NPCTypeSystem.get_context_modifiers(context)
    
    combined = NPCTypeSystem.combine_modifiers(role_mods, arch_mods, ctx_mods)
    
    print(f"Role: {role.value}")
    print(f"Archetype: {archetype.value}")
    print(f"Context: {context.value}")
    print(f"Starting Receptiveness: {combined.base_receptiveness:.2f}")
    print(f"Battery Drain Multiplier: {combined.battery_drain_multiplier:.2f}x")
    print(f"Time Pressure: {combined.time_pressure}")
    print(f"Comfortable Silence: {combined.comfortable_silence}")
    print()
    
    # Example 2: Party extrovert
    print("=== Example 2: Party Extrovert ===")
    role = NPCRole.SOCIAL
    archetype = PersonalityArchetype.EXTROVERT
    context = SocialContext.SOCIALIZING
    
    role_mods = NPCTypeSystem.get_role_modifiers(role)
    arch_mods = NPCTypeSystem.get_archetype_modifiers(archetype)
    ctx_mods = NPCTypeSystem.get_context_modifiers(context)
    
    combined = NPCTypeSystem.combine_modifiers(role_mods, arch_mods, ctx_mods)
    
    print(f"Role: {role.value}")
    print(f"Archetype: {archetype.value}")
    print(f"Context: {context.value}")
    print(f"Starting Receptiveness: {combined.base_receptiveness:.2f}")
    print(f"Battery Drain Multiplier: {combined.battery_drain_multiplier:.2f}x")
    print(f"Failure Tolerance Modifier: +{combined.failure_tolerance_modifier}")
    print(f"Carries Conversation: {combined.carries_conversation}")
    print()
    
    # Example 3: Neighbor you've never talked to
    print("=== Example 3: Neighbor ===")
    role = NPCRole.NEIGHBOR
    archetype = PersonalityArchetype.BALANCED
    context = SocialContext.LEISURE
    
    role_mods = NPCTypeSystem.get_role_modifiers(role)
    arch_mods = NPCTypeSystem.get_archetype_modifiers(archetype)
    ctx_mods = NPCTypeSystem.get_context_modifiers(context)
    
    combined = NPCTypeSystem.combine_modifiers(role_mods, arch_mods, ctx_mods)
    
    print(f"Role: {role.value}")
    print(f"Archetype: {archetype.value}")
    print(f"Context: {context.value}")
    print(f"Starting Bond: {combined.base_bond:.2f}")
    print(f"Starting Receptiveness: {combined.base_receptiveness:.2f}")
    print(f"Battery Drain Multiplier: {combined.battery_drain_multiplier:.2f}x")
    print()

if __name__ == "__main__":
    example_usage()