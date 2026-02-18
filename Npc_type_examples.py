#!/usr/bin/env python3
"""
Example script demonstrating different NPC type combinations
Shows how role, archetype, and context combine to create varied NPCs
"""

from npc_types import (
    NPCRole, PersonalityArchetype, SocialContext,
    NPCTypeSystem, NPCTypeGenerator
)

def print_npc_profile(role, archetype, context):
    """Print a detailed profile of an NPC type combination"""
    
    print(f"\n{'='*70}")
    print(f"NPC PROFILE")
    print(f"{'='*70}")
    print(f"Role: {role.value}")
    print(f"Archetype: {archetype.value}")
    print(f"Context: {context.value}")
    print(f"{'-'*70}")
    
    # Get individual modifiers
    role_mods = NPCTypeSystem.get_role_modifiers(role)
    arch_mods = NPCTypeSystem.get_archetype_modifiers(archetype)
    ctx_mods = NPCTypeSystem.get_context_modifiers(context)
    
    # Combine
    combined = NPCTypeSystem.combine_modifiers(role_mods, arch_mods, ctx_mods)
    
    # Display combined stats
    print(f"\nStarting Stats:")
    print(f"  Receptiveness: {combined.base_receptiveness:.2f}/10")
    print(f"  Bond: {combined.base_bond:.2f}/10")
    
    print(f"\nBehavioral Traits:")
    print(f"  Conversation Patience: {combined.conversation_patience:.2f}x")
    print(f"  Time Pressure: {'Yes ⏰' if combined.time_pressure else 'No'}")
    print(f"  Domain Boost: +{int(combined.domain_boost * 100)}% for shared interests")
    
    print(f"\nPlayer Impact:")
    print(f"  Battery Drain: {combined.battery_drain_multiplier:.2f}x")
    print(f"  Failure Tolerance Mod: {combined.failure_tolerance_modifier:+d}")
    
    print(f"\nSpecial Traits:")
    traits = []
    if combined.carries_conversation:
        traits.append("🗣️  Carries conversation (talkative)")
    if combined.comfortable_silence:
        traits.append("🤫 Comfortable with silence")
    if combined.critical_of_flirting:
        traits.append("🤨 Critical of flirting (-30%)")
    if combined.enthusiastic_about_interests:
        traits.append("✨ Enthusiastic about interests")
    if not combined.exits_gracefully:
        traits.append("🚶 May exit abruptly")
    
    if traits:
        for trait in traits:
            print(f"  {trait}")
    else:
        print(f"  None")
    
    print(f"\nInterpretation:")
    print(f"  {interpret_combination(role, archetype, context, combined)}")

def interpret_combination(role, archetype, context, mods):
    """Generate a human-readable interpretation of the NPC type"""
    
    interpretations = []
    
    # Receptiveness interpretation
    if mods.base_receptiveness < 1.5:
        interpretations.append("Very guarded and hard to approach")
    elif mods.base_receptiveness < 2.0:
        interpretations.append("Somewhat reserved initially")
    elif mods.base_receptiveness < 2.3:
        interpretations.append("Reasonably open to conversation")
    else:
        interpretations.append("Very receptive and friendly")
    
    # Battery interpretation
    if mods.battery_drain_multiplier > 1.3:
        interpretations.append("exhausting to interact with")
    elif mods.battery_drain_multiplier > 1.1:
        interpretations.append("moderately draining")
    elif mods.battery_drain_multiplier < 0.9:
        interpretations.append("easier on your social battery")
    else:
        interpretations.append("standard social energy cost")
    
    # Special behaviors
    if mods.time_pressure:
        interpretations.append("in a hurry")
    
    if mods.carries_conversation:
        interpretations.append("will do most of the talking")
    
    if mods.comfortable_silence:
        interpretations.append("appreciates brief exchanges")
    
    return "; ".join(interpretations) + "."

def main():
    """Run example demonstrations"""
    
    print("\n" + "="*70)
    print(" NPC TYPE SYSTEM DEMONSTRATIONS")
    print("="*70)
    
    # Example 1: Busy barista who's an introvert
    print_npc_profile(
        NPCRole.SERVICE_WORKER,
        PersonalityArchetype.INTROVERT,
        SocialContext.WORKING
    )
    
    # Example 2: Enthusiastic party-goer
    print_npc_profile(
        NPCRole.SOCIAL,
        PersonalityArchetype.ENTHUSIAST,
        SocialContext.SOCIALIZING
    )
    
    # Example 3: Skeptical stranger
    print_npc_profile(
        NPCRole.STRANGER,
        PersonalityArchetype.SKEPTIC,
        SocialContext.TASK_FOCUSED
    )
    
    # Example 4: Extroverted neighbor
    print_npc_profile(
        NPCRole.NEIGHBOR,
        PersonalityArchetype.EXTROVERT,
        SocialContext.LEISURE
    )
    
    # Example 5: Relaxed coffee shop browser
    print_npc_profile(
        NPCRole.LEISURE,
        PersonalityArchetype.BALANCED,
        SocialContext.LEISURE
    )
    
    # Example 6: Professional contact at networking event
    print_npc_profile(
        NPCRole.PROFESSIONAL,
        PersonalityArchetype.BALANCED,
        SocialContext.SOCIALIZING
    )
    
    print(f"\n{'='*70}")
    print("AUTO-SUGGESTION EXAMPLES")
    print(f"{'='*70}\n")
    
    # Test auto-suggestion
    locations = [
        "Coffee shop",
        "Bar on Friday night",
        "Office meeting room",
        "Sidewalk downtown",
        "Apartment building hallway",
        "Gym locker room"
    ]
    
    for location in locations:
        suggested_role = NPCTypeGenerator.suggest_role_from_location(location)
        suggested_context = NPCTypeGenerator.suggest_context_from_location(location)
        random_archetype = NPCTypeGenerator.random_archetype()
        
        print(f"Location: '{location}'")
        print(f"  → Suggested Role: {suggested_role.value}")
        print(f"  → Suggested Context: {suggested_context.value}")
        print(f"  → Random Archetype: {random_archetype.value}")
        print()

if __name__ == "__main__":
    main()