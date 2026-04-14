LIGHTING_MAP = {
    "natural_warm": "warm natural daylight, soft ambient lighting",
    "soft_side": "soft side lighting, controlled shadows, elegant falloff",
    "cinematic_blue": "cinematic blue tones, cool dramatic lighting",
    "luxury_reflective": "luxury studio lighting, subtle reflections on surface",
    "dim_dramatic": "dim dramatic lighting, deep shadows, moody atmosphere",
    "clean_studio": "clean studio lighting, even illumination, professional",
    "golden_hour": "golden hour lighting, warm orange tones, long shadows",
    "neon_urban": "urban neon lighting, colorful reflections on wet surfaces",
}

CAMERA_MAP = {
    "slow_dolly_in": "slow cinematic dolly-in camera movement",
    "orbit": "smooth orbit around subject, 360 pan",
    "static": "static locked-off camera, no movement",
    "tracking_shot": "steady tracking shot following subject from behind",
    "low_angle_hero": "low angle hero shot, looking up at subject",
    "handheld_cinematic": "subtle handheld cinematic movement, slight natural sway",
    "push_in_reveal": "slow push-in reveal, gradual approach to detail",
    "top_down": "top-down overhead shot, birds eye view",
    "rack_focus": "rack focus transition, shifting depth of field",
}

SHOT_MAP = {
    "wide": "wide establishing shot",
    "full": "full shot showing complete subject",
    "medium": "medium shot, waist up",
    "closeup": "close-up shot on key details",
    "macro": "extreme macro close-up, ultra detail",
    "wide_to_close": "starts wide, slowly pushes to close-up",
}

DOF_MAP = {
    "shallow_dof": "shallow depth of field, beautiful bokeh background blur",
    "medium_dof": "medium depth of field, balanced focus",
    "deep_dof": "deep depth of field, everything in sharp focus",
}

PACE_MAP = {
    "slow_paced": "slow deliberate pacing, contemplative rhythm",
    "medium_paced": "balanced moderate pacing",
    "fast_paced": "fast dynamic pacing, energetic rhythm",
}

VIDEO_TYPE_MAP = {
    "product_ad": "product advertisement",
    "cinematic_scene": "cinematic scene",
    "social_reel": "social media reel",
    "ugc": "UGC-style authentic video",
    "product_closeup": "product close-up showcase",
    "music_visual": "music visual",
    "short_story": "short narrative story",
    "launch_ad": "launch advertisement",
}

GOAL_MAP = {
    "sell_convert": "sell and convert viewers into buyers",
    "spark_curiosity": "spark curiosity and intrigue",
    "convey_luxury": "convey luxury and premium quality",
    "brand_identity": "build strong brand identity",
    "storytelling": "tell a compelling story",
    "entertain": "entertain and delight the audience",
}

MOOD_MAP = {
    "luxury_calm": "luxurious and calm",
    "energetic_fast": "energetic and fast-paced",
    "dramatic_emotional": "dramatic and emotional",
    "clean_professional": "clean and professional",
    "warm_intimate": "warm and intimate",
    "bold_powerful": "bold and powerful",
}

# Arabic label maps for display prompt
LIGHTING_AR = {
    "natural_warm": "إضاءة طبيعية دافئة",
    "soft_side": "إضاءة جانبية ناعمة",
    "cinematic_blue": "إضاءة سينمائية زرقاء",
    "luxury_reflective": "إضاءة فاخرة معكوسة",
    "dim_dramatic": "إضاءة خافتة درامية",
    "clean_studio": "إضاءة استوديو نظيفة",
    "golden_hour": "إضاءة الساعة الذهبية",
    "neon_urban": "إضاءة نيون حضرية",
}

CAMERA_AR = {
    "slow_dolly_in": "دولي-إن بطيء",
    "orbit": "دوران حول الموضوع",
    "static": "ثابتة",
    "tracking_shot": "تتبع من الخلف",
    "low_angle_hero": "زاوية منخفضة بطولية",
    "handheld_cinematic": "محمولة سينمائية",
    "push_in_reveal": "اقتراب تدريجي كاشف",
    "top_down": "من الأعلى",
    "rack_focus": "تغيير بؤري",
}

SHOT_AR = {
    "wide": "لقطة واسعة",
    "full": "لقطة كاملة",
    "medium": "لقطة متوسطة",
    "closeup": "لقطة قريبة",
    "macro": "لقطة ماكرو",
    "wide_to_close": "من واسعة إلى قريبة",
}

VIDEO_TYPE_AR = {
    "product_ad": "إعلان منتج",
    "cinematic_scene": "مشهد سينمائي",
    "social_reel": "ريلز سوشال",
    "ugc": "فيديو UGC",
    "product_closeup": "عرض منتج قريب",
    "music_visual": "فيجوال موسيقي",
    "short_story": "قصة قصيرة",
    "launch_ad": "إعلان إطلاق",
}

GOAL_AR = {
    "sell_convert": "يبيع ويحوّل",
    "spark_curiosity": "يثير الفضول",
    "convey_luxury": "يوصل الفخامة",
    "brand_identity": "يبني الهوية",
    "storytelling": "يحكي قصة",
    "entertain": "يمتع ويطرب",
}

MOOD_AR = {
    "luxury_calm": "فاخر وهادئ",
    "energetic_fast": "حيوي وسريع",
    "dramatic_emotional": "درامي وعاطفي",
    "clean_professional": "نظيف ومحترف",
    "warm_intimate": "دافئ وحميمي",
    "bold_powerful": "قوي وجريء",
}

FIXED_AR = {
    "identity": "هوية الشخصية / الشكل",
    "product_shape": "شكل المنتج / العبوة",
    "colors": "ألوان المشهد",
    "lighting_style": "نوع الإضاءة",
    "background": "المكان / الخلفية",
    "clothing": "الملابس",
    "logo": "الشعار أو العلامة التجارية",
    "tone": "النبرة العامة",
}

FIXED_EN = {
    "identity": "character/person identity and appearance",
    "product_shape": "product shape and packaging",
    "colors": "scene color palette",
    "lighting_style": "lighting style",
    "background": "location and background",
    "clothing": "clothing and wardrobe",
    "logo": "logo and brand marks",
    "tone": "overall tone and mood",
}

AVOID_AR = {
    "hand_deformities": "تشوهات الأيدي",
    "weird_expressions": "تعابير وجه غريبة",
    "aggressive_camera": "حركة كاميرا عدوانية",
    "oversaturated": "ألوان مشبعة جداً",
    "busy_background": "خلفية مزدحمة",
    "distorted_text": "نصوص مشوهة",
    "unrealistic_motion": "حركات غير واقعية",
    "random_elements": "عناصر عشوائية",
    "flickering": "وميض",
    "excessive_effects": "مبالغة في المؤثرات",
}

AVOID_EN = {
    "hand_deformities": "hand and finger deformities",
    "weird_expressions": "unnatural facial expressions",
    "aggressive_camera": "aggressive or jarring camera movement",
    "oversaturated": "oversaturated colors",
    "busy_background": "cluttered or busy backgrounds",
    "distorted_text": "distorted or unreadable text",
    "unrealistic_motion": "unrealistic or physics-defying motion",
    "random_elements": "random unrelated elements appearing",
    "flickering": "flickering or strobing artifacts",
    "excessive_effects": "excessive visual effects or filters",
}


def build_prompts(data: dict) -> dict:
    video_type = data.get("video_type", "")
    goal = data.get("goal", "")
    mood = data.get("mood", "")
    subject = data.get("subject", "")
    environment = data.get("environment", "")
    lighting = data.get("lighting", "")
    camera_movement = data.get("camera_movement", "")
    shot_type = data.get("shot_type", "")
    depth_of_field = data.get("depth_of_field", "")
    pace = data.get("pace", "")
    fixed_elements = data.get("fixed_elements", [])
    avoid_elements = data.get("avoid_elements", [])
    avoid_extra = data.get("avoid_extra", "")
    ref_character = data.get("ref_character")
    ref_lighting = data.get("ref_lighting")
    ref_camera = data.get("ref_camera")
    ref_audio = data.get("ref_audio")

    # English prompt
    video_type_en = VIDEO_TYPE_MAP.get(video_type, video_type)
    goal_en = GOAL_MAP.get(goal, goal)
    mood_en = MOOD_MAP.get(mood, mood)
    lighting_en = LIGHTING_MAP.get(lighting, lighting)
    camera_en = CAMERA_MAP.get(camera_movement, camera_movement)
    shot_en = SHOT_MAP.get(shot_type, shot_type)
    dof_en = DOF_MAP.get(depth_of_field, depth_of_field)
    pace_en = PACE_MAP.get(pace, pace)

    fixed_en_list = [FIXED_EN.get(f, f) for f in fixed_elements]
    fixed_en_str = ", ".join(fixed_en_list) if fixed_en_list else "overall visual consistency"

    avoid_en_list = [AVOID_EN.get(a, a) for a in avoid_elements]
    if avoid_extra:
        avoid_en_list.append(avoid_extra)
    avoid_en_str = ", ".join(avoid_en_list) if avoid_en_list else "common AI artifacts"

    english_prompt = (
        f"Create a {video_type_en} featuring {subject} inside {environment}.\n\n"
        f"Lighting: {lighting_en}.\n"
        f"Camera: {camera_en}, {shot_en}.\n"
        f"Depth of field: {dof_en}.\n"
        f"Pacing: {pace_en}.\n\n"
        f"Visual style: {mood_en} aesthetic. Goal: {goal_en}.\n\n"
        f"Keep consistent throughout: {fixed_en_str}.\n"
    )

    if ref_character and ref_character.get("url"):
        desc = ref_character.get("description", "")
        english_prompt += f"\nCharacter/product reference provided — maintain exact appearance. {desc}\n"
    if ref_lighting and ref_lighting.get("url"):
        desc = ref_lighting.get("description", "")
        english_prompt += f"\nLighting reference provided — match the lighting style. {desc}\n"
    if ref_camera and ref_camera.get("url"):
        desc = ref_camera.get("description", "")
        english_prompt += f"\nCamera movement reference provided — replicate camera style. {desc}\n"
    if ref_audio and ref_audio.get("url"):
        desc = ref_audio.get("description", "")
        english_prompt += f"\nAudio reference provided — synchronize rhythm and pacing. {desc}\n"

    english_prompt += (
        f"\nThe final output should feel like {goal_en} with {mood_en} quality.\n\n"
        f"Avoid: {avoid_en_str}.\n"
        f"Technical quality: cinematic 4K, photorealistic detail, professional film production, "
        f"high fidelity textures, smooth motion, no AI artifacts."
    )

    # Arabic prompt
    video_type_ar = VIDEO_TYPE_AR.get(video_type, video_type)
    goal_ar = GOAL_AR.get(goal, goal)
    mood_ar = MOOD_AR.get(mood, mood)
    lighting_ar = LIGHTING_AR.get(lighting, lighting)
    camera_ar = CAMERA_AR.get(camera_movement, camera_movement)
    shot_ar = SHOT_AR.get(shot_type, shot_type)

    fixed_ar_list = [FIXED_AR.get(f, f) for f in fixed_elements]
    fixed_ar_str = "، ".join(fixed_ar_list) if fixed_ar_list else "التناسق البصري العام"

    avoid_ar_list = [AVOID_AR.get(a, a) for a in avoid_elements]
    if avoid_extra:
        avoid_ar_list.append(avoid_extra)
    avoid_ar_str = "، ".join(avoid_ar_list) if avoid_ar_list else "عيوب الذكاء الاصطناعي الشائعة"

    arabic_prompt = (
        f"فيديو {video_type_ar} يعرض {subject} في {environment}.\n\n"
        f"الإضاءة: {lighting_ar}.\n"
        f"الكاميرا: {camera_ar}، {shot_ar}.\n"
        f"الهدف: {goal_ar}. الجو العام: {mood_ar}.\n\n"
        f"الثوابت: {fixed_ar_str}.\n"
    )

    if ref_character and ref_character.get("url"):
        arabic_prompt += "\nمرجع الشخصية/المنتج مرفق — الحفاظ على المظهر الدقيق.\n"
    if ref_lighting and ref_lighting.get("url"):
        arabic_prompt += "\nمرجع الإضاءة مرفق — مطابقة أسلوب الإضاءة.\n"
    if ref_camera and ref_camera.get("url"):
        arabic_prompt += "\nمرجع حركة الكاميرا مرفق — تكرار أسلوب الحركة.\n"
    if ref_audio and ref_audio.get("url"):
        arabic_prompt += "\nمرجع صوتي مرفق — مزامنة الإيقاع والسرعة.\n"

    arabic_prompt += f"\nتجنب: {avoid_ar_str}."

    return {
        "arabic_prompt": arabic_prompt.strip(),
        "english_prompt": english_prompt.strip(),
    }
