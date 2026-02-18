#!/usr/bin/env python3
"""
Introvert Social RPG - Main Game Engine
A text-based RPG simulating social interactions for introverts
"""

import random
import json
from dataclasses import dataclass, field, asdict
from typing import List, Dict, Optional, Tuple
from enum import Enum
import anthropic
import os

# Import NPC type system
from npc_types import (
    NPCRole, PersonalityArchetype, SocialContext,
    NPCTypeModifiers, NPCTypeSystem, NPCTypeGenerator
)

# ============================================================================
# ENUMS AND CONSTANTS
# ============================================================================

class AttractionLevel(Enum):
    NEUTRAL = "neutral"
    PLATONIC = "platonic"
    ROMANTIC = "romantic"

class RiskLevel(Enum):
    SAFE = "safe"              # 75-92%
    MODERATE = "moderate"      # 55-75%
    RISKY = "risky"           # 35-55%
    VERY_RISKY = "very_risky" # <35%

class ExchangeOutcome(Enum):
    VERY_POSITIVE = "very_positive"
    POSITIVE = "positive"
    NEUTRAL = "neutral"
    NEGATIVE = "negative"
    FAILED = "failed"

# ============================================================================
# DATA CLASSES
# ============================================================================

@dataclass
class CharacterStats:
    """Player character statistics"""
    eloquence: int = 0
    emotional_intelligence: int = 0
    body_language_perception: int = 0
    persuasion: int = 0
    acting: int = 0
    intuition: int = 0
    
    # Derived stats
    social_battery: int = 50  # -50 to +50 for introverts
    emotional_bandwidth: int = 100  # 0 to 100
    
    # Background
    profession: str = ""
    hobbies: List[str] = field(default_factory=list)
    location: str = ""
    
    def total_points(self) -> int:
        return (self.eloquence + self.emotional_intelligence + 
                self.body_language_perception + self.persuasion + 
                self.acting + self.intuition)
    
    def get_domain_bonus(self, topic: str) -> Dict[str, int]:
        """Returns stat bonuses if topic matches profession/hobbies"""
        bonuses = {}
        
        # Check if topic relates to profession or hobbies
        is_domain = (topic.lower() in self.profession.lower() or 
                    any(topic.lower() in hobby.lower() for hobby in self.hobbies))
        
        if not is_domain:
            return bonuses
            
        # Apply bonuses to stats <= 1
        for stat_name in ['eloquence', 'acting', 'persuasion', 'intuition']:
            stat_value = getattr(self, stat_name)
            if stat_value <= 1:
                bonus = random.randint(1, 3)
                bonuses[stat_name] = bonus
                
        return bonuses

@dataclass
class NPCState:
    """State of an NPC during interaction"""
    name: str
    description: str
    age_range: str
    appearance: str
    personality: str
    background: str
    interests: List[str]
    
    # NPC Type information
    role: Optional[NPCRole] = None
    archetype: Optional[PersonalityArchetype] = None
    social_context: Optional[SocialContext] = None
    type_modifiers: Optional[NPCTypeModifiers] = None
    
    # Interaction state
    receptiveness: float = 2.0  # 0-10 scale
    bond: float = 0.0  # 0-10 scale
    consecutive_positives: int = 0
    
    # Attraction
    attraction_level: AttractionLevel = AttractionLevel.NEUTRAL
    base_flirt_success: int = 90  # Will be rolled on first romantic approach
    flirt_uses: int = 0
    
    # Failure tracking for bond-based resilience
    failures_this_interaction: int = 0
    
    # Acting/Disinterest tracking
    disinterest_signals: int = 0  # Tracks accidental disinterest shown
    
    def can_tolerate_failure(self) -> bool:
        """Determines if NPC will continue conversation after failure based on bond"""
        # Base tolerance by bond level
        if self.bond < 1.0:
            base_tolerance = 1
        elif self.bond < 2.0:
            base_tolerance = 2
        elif self.bond < 3.0:
            base_tolerance = 2
        elif self.bond < 4.0:
            base_tolerance = 3
        else:  # bond >= 4.0
            base_tolerance = 4
        
        # Apply type modifier
        if self.type_modifiers:
            base_tolerance = NPCTypeSystem.adjust_failure_tolerance(
                base_tolerance, self.type_modifiers
            )
        
        return self.failures_this_interaction < base_tolerance
    
    def get_flirt_success_rate(self) -> int:
        """Calculate current flirt success rate with degradation"""
        base = self.base_flirt_success
        
        # Degradation per use
        degradation = self.flirt_uses * 20
        
        # Bond-based restoration
        if self.bond < 1.0:
            restoration = self.consecutive_positives * 2
        elif self.bond < 2.0:
            restoration = self.consecutive_positives * 3
        elif self.bond < 3.0:
            restoration = self.consecutive_positives * 4
        elif self.bond < 4.0:
            restoration = self.consecutive_positives * 5
        else:
            restoration = self.consecutive_positives * 6
            
        rate = base - degradation + restoration
        return max(10, min(100, rate))  # Clamp between 10-100

@dataclass
class DialogueChoice:
    """A dialogue option presented to the player"""
    text: str
    risk_level: RiskLevel
    base_success_rate: int
    requires_stats: Dict[str, int]
    is_flirt: bool = False
    is_disinterest_bridge: bool = False  # Special option to connect topic to domain
    topic: Optional[str] = None

@dataclass
class InteractionContext:
    """Current context of an interaction"""
    npc: NPCState
    player: CharacterStats
    location: str
    time_of_day: str
    momentum_bonus: int = 0  # +2% per consecutive positive, capped by risk level
    domain_active: Optional[str] = None
    
    def get_momentum_cap(self, risk: RiskLevel) -> int:
        """Returns max momentum bonus for given risk level"""
        caps = {
            RiskLevel.SAFE: 10,      # 5 positives
            RiskLevel.MODERATE: 12,   # 6 positives
            RiskLevel.RISKY: 14,      # 7 positives
            RiskLevel.VERY_RISKY: 16  # 8 positives
        }
        return caps[risk]

# ============================================================================
# GAME ENGINE
# ============================================================================

class IntrovertRPG:
    """Main game engine"""
    
    def __init__(self, api_key: str = None):
        if api_key:
            self.client = anthropic.Anthropic(api_key=api_key)
        else:
            self.client = anthropic.Anthropic()  # Uses ANTHROPIC_AUTH_TOKEN from env
        self.player: Optional[CharacterStats] = None
        self.current_interaction: Optional[InteractionContext] = None
        self.conversation_history: List[Dict] = []
        
    # ========================================================================
    # CHARACTER CREATION
    # ========================================================================
    
    def create_character(self, stats: Dict[str, int], profession: str, 
                        hobbies: List[str], location: str) -> CharacterStats:
        """Create player character"""
        char = CharacterStats(
            eloquence=stats.get('eloquence', 0),
            emotional_intelligence=stats.get('emotional_intelligence', 0),
            body_language_perception=stats.get('body_language_perception', 0),
            persuasion=stats.get('persuasion', 0),
            acting=stats.get('acting', 0),
            intuition=stats.get('intuition', 0),
            profession=profession,
            hobbies=hobbies,
            location=location
        )
        
        if char.total_points() != 15:
            raise ValueError(f"Stats must total 15 points, got {char.total_points()}")
            
        self.player = char
        return char
    
    # ========================================================================
    # NPC GENERATION
    # ========================================================================
    
    def generate_npc(self, location: str, context: str = "",
                    role: Optional[NPCRole] = None,
                    archetype: Optional[PersonalityArchetype] = None,
                    social_context: Optional[SocialContext] = None) -> NPCState:
        """Use Claude to generate a contextual NPC with optional type specification"""
        
        # Auto-suggest types if not provided
        if role is None:
            role = NPCTypeGenerator.suggest_role_from_location(location)
        
        if archetype is None:
            archetype = NPCTypeGenerator.random_archetype()
        
        if social_context is None:
            social_context = NPCTypeGenerator.suggest_context_from_location(location)
        
        # Get type-specific additions for prompt
        type_context = NPCTypeGenerator.generate_prompt_additions(
            role, archetype, social_context
        )
        
        prompt = f"""Generate a realistic NPC character for a social interaction RPG.

Location: {location}
Context: {context}

NPC Type Context:
{type_context}

Create a character with:
1. Name (first name only, or just role like "Barista")
2. Age range (e.g., "early 20s", "mid-30s")
3. Brief physical description (2-3 sentences, natural details)
4. Personality traits (2-3 key traits that match the archetype)
5. Brief background (1-2 sentences)
6. 2-3 interests/hobbies

Make them feel like a real person you might encounter in this location.
Keep it concise and natural.
The personality should reflect the type context provided.

Return ONLY valid JSON in this exact format:
{{
    "name": "string",
    "age_range": "string",
    "appearance": "string",
    "personality": "string",
    "background": "string",
    "interests": ["string", "string"]
}}"""

        response = self.client.messages.create(
            model="claude-opus-4-20250514",
            max_tokens=500,
            messages=[{"role": "user", "content": prompt}]
        )
        
        # Parse JSON response
        content = response.content[0].text.strip()
        # Remove markdown code blocks if present
        if content.startswith("```"):
            content = content.split("```")[1]
            if content.startswith("json"):
                content = content[4:]
        content = content.strip()
        
        npc_data = json.loads(content)
        
        # Create full description
        description = f"{npc_data['age_range']}, {npc_data['appearance']}"
        
        # Create NPC state
        npc = NPCState(
            name=npc_data['name'],
            description=description,
            age_range=npc_data['age_range'],
            appearance=npc_data['appearance'],
            personality=npc_data['personality'],
            background=npc_data['background'],
            interests=npc_data['interests'],
            role=role,
            archetype=archetype,
            social_context=social_context
        )
        
        # Apply type modifiers
        role_mods = NPCTypeSystem.get_role_modifiers(role)
        arch_mods = NPCTypeSystem.get_archetype_modifiers(archetype)
        ctx_mods = NPCTypeSystem.get_context_modifiers(social_context)
        
        combined_mods = NPCTypeSystem.combine_modifiers(role_mods, arch_mods, ctx_mods)
        
        NPCTypeSystem.apply_modifiers_to_npc(npc, combined_mods)
        
        return npc
    
    # ========================================================================
    # ATTRACTION SYSTEM
    # ========================================================================
    
    def determine_attraction(self, approach_choice: str, npc: NPCState) -> AttractionLevel:
        """
        Player chooses how they're approaching the interaction:
        A) Neutral - just task/transaction
        B) Platonic - friendly, wants to chat
        C) Romantic - attracted to them
        """
        attraction_map = {
            'A': AttractionLevel.NEUTRAL,
            'B': AttractionLevel.PLATONIC,
            'C': AttractionLevel.ROMANTIC
        }
        
        attraction = attraction_map.get(approach_choice, AttractionLevel.NEUTRAL)
        
        # Roll NPC's attraction if romantic approach
        if attraction == AttractionLevel.ROMANTIC:
            roll = random.randint(1, 100)
            if roll <= 5:  # 5% - No attraction
                npc.base_flirt_success = 10
            elif roll <= 20:  # 15% - Low attraction  
                npc.base_flirt_success = 50
            elif roll <= 80:  # 60% - Neutral/Medium attraction
                npc.base_flirt_success = 70
            else:  # 20% - High attraction
                npc.base_flirt_success = 90
            
            # Apply type modifier to flirt success
            if npc.type_modifiers:
                npc.base_flirt_success = NPCTypeSystem.adjust_flirt_success(
                    npc.base_flirt_success, npc.type_modifiers
                )
        
        return attraction
    
    # ========================================================================
    # DIALOGUE GENERATION
    # ========================================================================
    
    def generate_dialogue_choices(self, context: InteractionContext, 
                                  current_situation: str) -> List[DialogueChoice]:
        """Use Claude to generate 4 dialogue choices with varying risk levels"""
        
        # Build context for Claude
        player_stats = asdict(context.player)
        npc_state = {
            'name': context.npc.name,
            'description': context.npc.description,
            'personality': context.npc.personality,
            'interests': context.npc.interests,
            'receptiveness': context.npc.receptiveness,
            'bond': context.npc.bond,
            'consecutive_positives': context.npc.consecutive_positives,
            'attraction': context.npc.attraction_level.value,
            'role': context.npc.role.value if context.npc.role else 'unknown',
            'archetype': context.npc.archetype.value if context.npc.archetype else 'unknown',
            'social_context': context.npc.social_context.value if context.npc.social_context else 'unknown'
        }
        
        # Add type-specific context
        type_notes = ""
        if context.npc.type_modifiers:
            mods = context.npc.type_modifiers
            notes = []
            if mods.time_pressure:
                notes.append("NPC is busy/time-pressured")
            if mods.carries_conversation:
                notes.append("NPC is talkative (extrovert)")
            if mods.comfortable_silence:
                notes.append("NPC appreciates brevity (introvert)")
            if mods.critical_of_flirting:
                notes.append("NPC is skeptical of flirting")
            if mods.enthusiastic_about_interests:
                notes.append("NPC gets very excited about their interests")
            
            if notes:
                type_notes = f"\nNPC Type Notes: {'; '.join(notes)}"
        
        prompt = f"""You are generating dialogue choices for a social interaction RPG.

CURRENT SITUATION:
{current_situation}

PLAYER STATS:
{json.dumps(player_stats, indent=2)}

NPC STATE:
{json.dumps(npc_state, indent=2)}{type_notes}

DOMAIN ACTIVE: {context.domain_active or "None"}
MOMENTUM BONUS: +{context.momentum_bonus}%

CRITICAL RULES:
1. Generate EXACTLY 4 dialogue choices
2. ONE must be Safe (75-92% base success)
3. ONE must be Moderate (55-75% base success)  
4. ONE must be Risky (35-55% base success)
5. ONE must be Very Risky (<35% base success)
6. RANDOMIZE the order - do not present in order of risk
7. Each choice should feel natural and distinct
8. Consider NPC type notes when generating options

RISK FACTORS:
- Safe: Simple, low-stakes, agreeable
- Moderate: Mild challenge, personal question, light disagreement
- Risky: Bold statement, vulnerable admission, challenging their view
- Very Risky: Very personal too soon, controversial, pushy

For {context.npc.attraction_level.value} interaction:
- Include appropriate flirt options if romantic
- Keep platonic options friendly but not flirty
- Keep neutral options transactional

Return ONLY valid JSON array with 4 choices:
[
    {{
        "text": "exact dialogue text",
        "risk_level": "safe|moderate|risky|very_risky",
        "base_success_rate": number (match risk level guidelines),
        "is_flirt": boolean,
        "topic": "optional topic string"
    }}
]"""

        response = self.client.messages.create(
            model="claude-opus-4-20250514",
            max_tokens=800,
            messages=[{"role": "user", "content": prompt}]
        )
        
        content = response.content[0].text.strip()
        if content.startswith("```"):
            content = content.split("```")[1]
            if content.startswith("json"):
                content = content[4:]
        content = content.strip()
        
        choices_data = json.loads(content)
        
        # Convert to DialogueChoice objects
        choices = []
        for choice_data in choices_data:
            risk_map = {
                'safe': RiskLevel.SAFE,
                'moderate': RiskLevel.MODERATE,
                'risky': RiskLevel.RISKY,
                'very_risky': RiskLevel.VERY_RISKY
            }
            
            choice = DialogueChoice(
                text=choice_data['text'],
                risk_level=risk_map[choice_data['risk_level']],
                base_success_rate=choice_data['base_success_rate'],
                requires_stats={},  # Could be populated based on choice content
                is_flirt=choice_data.get('is_flirt', False),
                topic=choice_data.get('topic')
            )
            choices.append(choice)
        
        return choices
    
    # ========================================================================
    # DIALOGUE RESOLUTION
    # ========================================================================
    
    def resolve_choice(self, choice: DialogueChoice, context: InteractionContext) -> Tuple[bool, ExchangeOutcome, str]:
        """
        Resolve a dialogue choice
        Returns: (success, outcome, response_text)
        """
        
        # Calculate success rate
        success_rate = choice.base_success_rate
        
        # Add momentum bonus (capped by risk level)
        momentum_cap = context.get_momentum_cap(choice.risk_level)
        actual_momentum = min(context.momentum_bonus, momentum_cap)
        success_rate += actual_momentum
        
        # Add domain bonuses if applicable
        if choice.topic and context.domain_active:
            bonuses = context.player.get_domain_bonus(choice.topic)
            # Domain bonuses could add 5-10% based on relevant stats
            domain_boost = sum(bonuses.values()) * 2  # 2% per bonus point
            success_rate += domain_boost
        
        # Flirt success rate (for romantic interactions)
        if choice.is_flirt and context.npc.attraction_level == AttractionLevel.ROMANTIC:
            flirt_rate = context.npc.get_flirt_success_rate()
            success_rate = flirt_rate  # Flirt has its own success calculation
        
        # Roll for success
        roll = random.randint(1, 100)
        success = roll <= success_rate
        
        # Generate NPC response using Claude
        response_text = self._generate_npc_response(choice, context, success)
        
        # Determine outcome and apply state changes
        outcome = self._determine_outcome(choice, success, context)
        self._apply_outcome(outcome, choice, context, success)
        
        return success, outcome, response_text
    
    def _generate_npc_response(self, choice: DialogueChoice, 
                               context: InteractionContext, success: bool) -> str:
        """Generate NPC's response to player's dialogue choice"""
        
        situation = f"""PLAYER SAID: "{choice.text}"
CHOICE RISK: {choice.risk_level.value}
OUTCOME: {"SUCCESS" if success else "FAILURE"}

NPC: {context.npc.name}
Personality: {context.npc.personality}
Current Receptiveness: {context.npc.receptiveness}/10
Current Bond: {context.npc.bond}/10
Attraction: {context.npc.attraction_level.value}

Generate the NPC's response. Should be:
- Natural and conversational
- Reflect their personality
- Match the success/failure outcome
- {"Warm and engaged" if success else "Cooler or pulling back"}
- 1-3 sentences typically

Response:"""

        response = self.client.messages.create(
            model="claude-opus-4-20250514",
            max_tokens=200,
            messages=[{"role": "user", "content": situation}]
        )
        
        return response.content[0].text.strip()
    
    def _determine_outcome(self, choice: DialogueChoice, success: bool, 
                          context: InteractionContext) -> ExchangeOutcome:
        """Determine the outcome quality of an exchange"""
        
        if not success:
            return ExchangeOutcome.FAILED
        
        # Successful exchanges vary by risk and bond
        if choice.risk_level == RiskLevel.VERY_RISKY and context.npc.bond >= 4.0:
            return ExchangeOutcome.VERY_POSITIVE
        elif choice.risk_level in [RiskLevel.RISKY, RiskLevel.VERY_RISKY]:
            return ExchangeOutcome.VERY_POSITIVE if random.random() > 0.5 else ExchangeOutcome.POSITIVE
        elif choice.risk_level == RiskLevel.MODERATE:
            return ExchangeOutcome.POSITIVE
        else:  # SAFE
            return ExchangeOutcome.POSITIVE if random.random() > 0.3 else ExchangeOutcome.NEUTRAL
    
    def _apply_outcome(self, outcome: ExchangeOutcome, choice: DialogueChoice,
                      context: InteractionContext, success: bool):
        """Apply state changes based on outcome"""
        
        npc = context.npc
        player = context.player
        attraction = npc.attraction_level
        
        # ====================================================================
        # SOCIAL BATTERY CHANGES (Harsher system)
        # ====================================================================
        
        if attraction == AttractionLevel.ROMANTIC:
            battery_changes = {
                ExchangeOutcome.VERY_POSITIVE: random.randint(2, 3),
                ExchangeOutcome.POSITIVE: random.randint(1, 2),
                ExchangeOutcome.NEUTRAL: random.randint(-3, -4),
                ExchangeOutcome.NEGATIVE: random.randint(-8, -10),
                ExchangeOutcome.FAILED: -(random.randint(18, 20) + 4)  # Base + failed penalty
            }
        elif attraction == AttractionLevel.PLATONIC:
            battery_changes = {
                ExchangeOutcome.VERY_POSITIVE: 1,
                ExchangeOutcome.POSITIVE: -1,
                ExchangeOutcome.NEUTRAL: random.randint(-4, -5),
                ExchangeOutcome.NEGATIVE: random.randint(-7, -9),
                ExchangeOutcome.FAILED: -(random.randint(14, 16) + 4)
            }
        else:  # NEUTRAL
            battery_changes = {
                ExchangeOutcome.VERY_POSITIVE: 0,
                ExchangeOutcome.POSITIVE: -2,
                ExchangeOutcome.NEUTRAL: random.randint(-5, -6),
                ExchangeOutcome.NEGATIVE: random.randint(-6, -8),
                ExchangeOutcome.FAILED: -(random.randint(15, 17) + 4)
            }
        
        player.social_battery += battery_changes[outcome]
        
        # Apply NPC type battery multiplier
        if npc.type_modifiers:
            # Recalculate with multiplier
            base_change = battery_changes[outcome]
            adjusted_change = NPCTypeSystem.adjust_battery_drain(
                base_change, npc.type_modifiers
            )
            # Replace the change
            player.social_battery -= base_change  # Remove original
            player.social_battery += adjusted_change  # Add adjusted
        
        player.social_battery = max(-50, min(50, player.social_battery))
        
        # ====================================================================
        # EMOTIONAL BANDWIDTH CHANGES (More punishing)
        # ====================================================================
        
        # Approach costs (initial interaction)
        if npc.bond == 0:
            approach_costs = {
                AttractionLevel.ROMANTIC: -7,
                AttractionLevel.PLATONIC: -5,
                AttractionLevel.NEUTRAL: -3
            }
            player.emotional_bandwidth += approach_costs[attraction]
        
        # Exchange costs
        if attraction == AttractionLevel.ROMANTIC:
            bandwidth_changes = {
                ExchangeOutcome.VERY_POSITIVE: random.randint(3, 5),
                ExchangeOutcome.POSITIVE: random.randint(1, 2),
                ExchangeOutcome.NEUTRAL: random.randint(-4, -5),
                ExchangeOutcome.NEGATIVE: random.randint(-8, -10),
                ExchangeOutcome.FAILED: -(random.randint(18, 26))  # 18 base + 3 failed + 5 sting
            }
        elif attraction == AttractionLevel.PLATONIC:
            bandwidth_changes = {
                ExchangeOutcome.VERY_POSITIVE: random.randint(1, 2),
                ExchangeOutcome.POSITIVE: 0,
                ExchangeOutcome.NEUTRAL: random.randint(-6, -7),
                ExchangeOutcome.NEGATIVE: random.randint(-7, -9),
                ExchangeOutcome.FAILED: -(random.randint(10, 13) + 3)
            }
        else:  # NEUTRAL
            bandwidth_changes = {
                ExchangeOutcome.VERY_POSITIVE: 0,
                ExchangeOutcome.POSITIVE: -2,
                ExchangeOutcome.NEUTRAL: random.randint(-7, -8),
                ExchangeOutcome.NEGATIVE: random.randint(-6, -8),
                ExchangeOutcome.FAILED: -(random.randint(9, 12) + 3)
            }
        
        player.emotional_bandwidth += bandwidth_changes[outcome]
        
        # Special rejection penalty for contact exchange failures
        if choice.is_flirt and not success:
            player.emotional_bandwidth -= 5  # Extra sting from rejection
        
        player.emotional_bandwidth = max(0, min(100, player.emotional_bandwidth))
        
        # ====================================================================
        # NPC STATE CHANGES
        # ====================================================================
        
        # Receptiveness changes (gradual)
        if outcome == ExchangeOutcome.VERY_POSITIVE:
            npc.receptiveness += random.uniform(0.75, 1.0)
        elif outcome == ExchangeOutcome.POSITIVE:
            npc.receptiveness += random.uniform(0.25, 0.5)
        elif outcome == ExchangeOutcome.NEUTRAL:
            npc.receptiveness += random.uniform(-0.25, 0)
        elif outcome == ExchangeOutcome.FAILED:
            npc.receptiveness += random.uniform(-0.5, -1.0)
        
        npc.receptiveness = max(0, min(10, npc.receptiveness))
        
        # Bond changes (gradual)
        if outcome == ExchangeOutcome.VERY_POSITIVE:
            npc.bond += random.uniform(0.75, 1.0)
        elif outcome == ExchangeOutcome.POSITIVE:
            npc.bond += random.uniform(0.25, 0.5)
        elif outcome == ExchangeOutcome.NEUTRAL:
            npc.bond += random.uniform(-0.25, 0)
        elif outcome == ExchangeOutcome.FAILED:
            npc.bond += random.uniform(-0.25, -0.5)
        
        npc.bond = max(0, min(10, npc.bond))
        
        # Momentum tracking
        if outcome in [ExchangeOutcome.VERY_POSITIVE, ExchangeOutcome.POSITIVE]:
            npc.consecutive_positives += 1
            context.momentum_bonus = npc.consecutive_positives * 2
        else:
            npc.consecutive_positives = 0
            context.momentum_bonus = 0
        
        # Failure tracking
        if outcome == ExchangeOutcome.FAILED:
            npc.failures_this_interaction += 1
        
        # Flirt tracking
        if choice.is_flirt:
            npc.flirt_uses += 1
    
    # ========================================================================
    # ACTING/DISINTEREST SYSTEM
    # ========================================================================
    
    def check_disinterest_trigger(self, topic: str, context: InteractionContext) -> bool:
        """Check if player shows accidental disinterest based on Acting stat"""
        
        # Exception cases (no risk)
        if topic and context.domain_active:
            if topic.lower() in context.domain_active.lower():
                return False  # Topic is in domain
        
        if context.npc.bond > 0 and "explicitly acknowledged" in context.npc.background:
            return False  # NPC knows it's not your interest
        
        # Romantic interactions have 50% reduction
        multiplier = 0.5 if context.npc.attraction_level == AttractionLevel.ROMANTIC else 1.0
        
        # Trigger rates by Acting stat
        trigger_rates = {
            0: 0.6,
            1: 0.6,
            2: 0.4,
            3: 0.2,
            4: 0.1,
            5: 0.1
        }
        
        rate = trigger_rates.get(context.player.acting, 0.4) * multiplier
        
        if random.random() < rate:
            context.npc.disinterest_signals += 1
            return True
        
        return False
    
    def apply_disinterest_consequence(self, context: InteractionContext) -> str:
        """Apply consequences of showing disinterest"""
        
        signals = context.npc.disinterest_signals
        
        if signals == 1:
            # Mild
            context.npc.receptiveness -= 0.25
            return f"{context.npc.name} notices you seem a bit distracted. 'Am I boring you?'"
        elif signals == 2:
            # Moderate
            context.npc.receptiveness -= 0.5
            context.npc.bond -= 0.25
            return f"{context.npc.name} pulls back slightly. 'You don't really care about this, do you?'"
        else:
            # Severe - conversation ends
            context.npc.receptiveness -= 1.0
            context.npc.bond -= 0.5
            return f"{context.npc.name} stops talking. The conversation has ended."
    
    # ========================================================================
    # GAME LOOP HELPERS
    # ========================================================================
    
    def start_interaction(self, npc: NPCState, location: str, time: str) -> InteractionContext:
        """Initialize a new interaction"""
        self.current_interaction = InteractionContext(
            npc=npc,
            player=self.player,
            location=location,
            time_of_day=time
        )
        return self.current_interaction
    
    def should_npc_exit(self, context: InteractionContext) -> Tuple[bool, str]:
        """Determine if NPC should exit the conversation"""
        
        # Check failure tolerance
        if not context.npc.can_tolerate_failure():
            return True, f"{context.npc.name} politely wraps up the conversation and leaves."
        
        # Check disinterest signals
        if context.npc.disinterest_signals >= 3:
            return True, f"{context.npc.name} has lost interest and ends the conversation."
        
        # Check if receptiveness dropped too low
        if context.npc.receptiveness < 1.0:
            return True, f"{context.npc.name} seems uncomfortable and makes an excuse to leave."
        
        return False, ""

# ============================================================================
# EXAMPLE USAGE
# ============================================================================

def main():
    """Example game session"""
    
    # Initialize game
    api_key = os.getenv("ANTHROPIC_API_KEY")
    auth_token = os.getenv("ANTHROPIC_AUTH_TOKEN")
    if not api_key and not auth_token:
        print("Please set ANTHROPIC_API_KEY or ANTHROPIC_AUTH_TOKEN environment variable")
        return

    game = IntrovertRPG(api_key)
    
    # Create character
    stats = {
        'eloquence': 3,
        'emotional_intelligence': 2,
        'body_language_perception': 3,
        'persuasion': 2,
        'acting': 2,
        'intuition': 3
    }
    
    player = game.create_character(
        stats=stats,
        profession="Graphic Designer",
        hobbies=["sketching", "urban exploration", "indie music"],
        location="Ypsilanti, Michigan"
    )
    
    print(f"Character created: {player.profession}")
    print(f"Stats: {stats}")
    print(f"Battery: {player.social_battery}/50")
    print(f"Bandwidth: {player.emotional_bandwidth}/100")
    print()
    
    # Generate NPC
    print("Generating NPC...")
    
    # Example: Generate a coffee shop barista who's an introvert and currently working
    npc = game.generate_npc(
        location="Coffee shop",
        context="Sunday morning, you're ordering coffee",
        role=NPCRole.SERVICE_WORKER,
        archetype=PersonalityArchetype.INTROVERT,
        social_context=SocialContext.WORKING
    )
    
    print(f"\nYou encounter: {npc.name}")
    print(f"Description: {npc.description}")
    print(f"Personality: {npc.personality}")
    print(f"Role: {npc.role.value if npc.role else 'Unknown'}")
    print(f"Archetype: {npc.archetype.value if npc.archetype else 'Unknown'}")
    print(f"Context: {npc.social_context.value if npc.social_context else 'Unknown'}")
    if npc.type_modifiers:
        print(f"Starting Receptiveness: {npc.receptiveness:.1f}/10 (type-modified)")
        print(f"Time Pressure: {'Yes' if npc.type_modifiers.time_pressure else 'No'}")
        print(f"Battery Drain Multiplier: {npc.type_modifiers.battery_drain_multiplier:.1f}x")
    print()
    
    # Start interaction
    print("How do you approach this interaction?")
    print("A) Neutral - just ordering coffee")
    print("B) Platonic - seems friendly, might chat")
    print("C) Romantic - attracted to them")
    choice = input("Choice (A/B/C): ").upper()
    
    attraction = game.determine_attraction(choice, npc)
    npc.attraction_level = attraction
    
    context = game.start_interaction(npc, "Coffee shop", "Sunday morning")
    
    print(f"\nApproach: {attraction.value}")
    if attraction == AttractionLevel.ROMANTIC:
        print(f"Base flirt success: {npc.base_flirt_success}%")
    print()
    
    # Interaction loop
    turn = 1
    while True:
        print(f"\n--- Turn {turn} ---")
        print(f"Battery: {player.social_battery}/50 | Bandwidth: {player.emotional_bandwidth}/100")
        print(f"Bond: {npc.bond:.1f} | Receptiveness: {npc.receptiveness:.1f}")
        print(f"Consecutive Positives: {npc.consecutive_positives} (Momentum: +{context.momentum_bonus}%)")
        print()
        
        # Check if NPC should exit
        should_exit, exit_msg = game.should_npc_exit(context)
        if should_exit:
            print(exit_msg)
            break
        
        # Generate dialogue choices
        situation = f"Turn {turn} of conversation with {npc.name}. Previous exchanges have built bond to {npc.bond:.1f}."
        
        print("Generating dialogue options...")
        choices = game.generate_dialogue_choices(context, situation)
        
        print("\nWhat do you say?")
        for i, choice in enumerate(choices, 1):
            flirt_marker = " [FLIRT]" if choice.is_flirt else ""
            print(f"{i}. {choice.text}{flirt_marker}")
        
        print("Q. End interaction")
        
        player_choice = input("\nChoice: ")
        
        if player_choice.upper() == 'Q':
            print("\nYou politely excuse yourself.")
            break
        
        try:
            choice_idx = int(player_choice) - 1
            selected_choice = choices[choice_idx]
        except (ValueError, IndexError):
            print("Invalid choice")
            continue
        
        # Resolve choice
        success, outcome, response = game.resolve_choice(selected_choice, context)
        
        print(f"\n{npc.name}: {response}")
        print(f"\nOutcome: {outcome.value} ({'SUCCESS' if success else 'FAILURE'})")
        
        turn += 1
        
        # Optional: limit turns
        if turn > 20:
            print("\nThe conversation has gone on for a while...")
            break
    
    # Summary
    print("\n=== Interaction Summary ===")
    print(f"Final Bond: {npc.bond:.1f}/10")
    print(f"Final Receptiveness: {npc.receptiveness:.1f}/10")
    print(f"Battery: {player.social_battery}/50")
    print(f"Bandwidth: {player.emotional_bandwidth}/100")
    print(f"Turns: {turn}")

if __name__ == "__main__":
    main()