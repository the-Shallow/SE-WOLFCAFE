# SafeBites - Unique Feature Ideas for Showcase

## Current Features Analysis

**What SafeBites Already Has:**
- ✅ Conversational AI search (LangGraph + FAISS)
- ✅ Allergen detection and filtering
- ✅ Semantic menu search
- ✅ Multi-intent query understanding
- ✅ Chat session management

**What's Missing (Opportunities):**
- Real-time features
- Visual/multimedia capabilities
- Advanced personalization
- Social/collaborative features
- Predictive/proactive features

---

## 🌟 Top 5 Unique Feature Ideas (Ranked by Impact)

### 1. 🍽️ **AI-Powered Meal Compatibility Score** ⭐⭐⭐⭐⭐

**Concept**: Real-time compatibility scoring between dishes and user dietary profiles using multi-factor analysis.

**Why It's Unique**:
- Goes beyond simple allergen filtering
- Provides transparency in AI decision-making
- Combines multiple data sources (allergens, nutrition, preferences, health goals)

**How It Works**:
```
User Profile:
- Allergens: peanuts, shellfish
- Health Goal: low-carb diet
- Preferences: spicy food, Italian cuisine
- Past Orders: vegetarian dishes (80% of time)

Dish: "Spicy Arrabbiata Pasta"
↓
AI Compatibility Analysis:
✅ Allergen Safety: 100% (no peanuts/shellfish)
⚠️ Nutrition Match: 45% (high carb - conflicts with low-carb goal)
✅ Taste Preference: 95% (spicy + Italian)
⚠️ Dietary Pattern: 60% (contains meat - user mostly vegetarian)
↓
Overall Compatibility Score: 75/100

Breakdown:
- Safety: ✅ SAFE (no allergens detected)
- Nutrition: ⚠️ MODERATE (high in carbs, moderate protein)
- Preference: ✅ GREAT MATCH (spicy, Italian)
- Habit: ⚠️ SLIGHT DEVIATION (usually vegetarian)

AI Suggestion: "Consider our vegetarian Spicy Penne Arrabbiata instead (92% match)"
```

**Implementation**:

```python
# models/compatibility_model.py
from pydantic import BaseModel
from typing import List, Dict

class CompatibilityScore(BaseModel):
    overall_score: float  # 0-100
    safety_score: float   # Allergen safety (0-100)
    nutrition_score: float  # Nutritional alignment (0-100)
    preference_score: float  # Taste/cuisine match (0-100)
    habit_score: float  # Historical pattern match (0-100)

    safety_status: str  # "SAFE", "CAUTION", "UNSAFE"
    breakdown: Dict[str, str]  # Detailed explanations
    alternatives: List[str]  # Suggested better matches
    confidence: float  # AI confidence in scoring

# services/compatibility_service.py
def calculate_compatibility(dish: dict, user_profile: dict) -> CompatibilityScore:
    """
    Calculate multi-dimensional compatibility score.

    Uses:
    - Rule-based allergen checking (100% accurate)
    - Nutrition comparison against health goals
    - Embedding similarity for taste preferences
    - Historical order pattern analysis
    """

    # 1. Safety Score (CRITICAL)
    safety_score, safety_status = check_allergen_safety(
        dish_allergens=dish.get("inferred_allergens", []),
        user_allergens=user_profile.get("allergen_preferences", [])
    )

    # 2. Nutrition Score
    nutrition_score = calculate_nutrition_alignment(
        dish_nutrition=dish.get("nutrition_facts", {}),
        user_goals=user_profile.get("health_goals", {})
    )

    # 3. Preference Score (using embeddings)
    preference_score = calculate_preference_match(
        dish_embedding=get_dish_embedding(dish),
        user_preferences=user_profile.get("taste_preferences", []),
        cuisine_type=dish.get("cuisine_type")
    )

    # 4. Habit Score (from order history)
    habit_score = calculate_habit_alignment(
        dish_categories=dish.get("categories", []),
        user_history=get_user_order_history(user_profile["_id"])
    )

    # Weighted overall score
    weights = {
        "safety": 0.40,      # 40% weight - most important
        "nutrition": 0.25,   # 25% weight
        "preference": 0.20,  # 20% weight
        "habit": 0.15        # 15% weight
    }

    overall = (
        safety_score * weights["safety"] +
        nutrition_score * weights["nutrition"] +
        preference_score * weights["preference"] +
        habit_score * weights["habit"]
    )

    # Generate explanation
    breakdown = generate_explanation(
        safety_score, nutrition_score,
        preference_score, habit_score,
        dish, user_profile
    )

    # Find better alternatives if score < 80
    alternatives = []
    if overall < 80:
        alternatives = find_better_alternatives(dish, user_profile, overall)

    return CompatibilityScore(
        overall_score=overall,
        safety_score=safety_score,
        nutrition_score=nutrition_score,
        preference_score=preference_score,
        habit_score=habit_score,
        safety_status=safety_status,
        breakdown=breakdown,
        alternatives=alternatives,
        confidence=calculate_confidence(dish)
    )

def check_allergen_safety(dish_allergens: List[dict], user_allergens: List[str]) -> tuple:
    """Check allergen safety with confidence scores."""
    if not user_allergens:
        return 100.0, "SAFE"

    detected_allergens = []
    for allergen_info in dish_allergens:
        allergen = allergen_info.get("allergen", "").lower()
        confidence = allergen_info.get("confidence", 0.0)

        if allergen in [a.lower() for a in user_allergens]:
            detected_allergens.append({
                "allergen": allergen,
                "confidence": confidence
            })

    if not detected_allergens:
        return 100.0, "SAFE"

    # Calculate safety score based on confidence
    max_confidence = max(a["confidence"] for a in detected_allergens)

    if max_confidence >= 0.8:
        return 0.0, "UNSAFE"
    elif max_confidence >= 0.5:
        return 50.0, "CAUTION"
    else:
        return 75.0, "CAUTION"

def calculate_nutrition_alignment(dish_nutrition: dict, user_goals: dict) -> float:
    """
    Compare dish nutrition against user health goals.

    User goals examples:
    - "low-carb": carbs < 30g per serving
    - "high-protein": protein > 20g per serving
    - "low-calorie": calories < 500 per serving
    """
    if not user_goals:
        return 100.0  # No goals = no penalty

    score = 100.0
    penalties = []

    for goal, constraint in user_goals.items():
        if goal == "low-carb":
            carbs = dish_nutrition.get("carbohydrates", {}).get("value", 0)
            if carbs > 30:
                penalty = min((carbs - 30) * 2, 50)  # Max 50 point penalty
                penalties.append(penalty)

        elif goal == "high-protein":
            protein = dish_nutrition.get("protein", {}).get("value", 0)
            if protein < 20:
                penalty = (20 - protein) * 2
                penalties.append(penalty)

        elif goal == "low-calorie":
            calories = dish_nutrition.get("calories", {}).get("value", 0)
            if calories > 500:
                penalty = min((calories - 500) / 10, 40)
                penalties.append(penalty)

    score -= sum(penalties)
    return max(score, 0.0)

def calculate_preference_match(dish_embedding, user_preferences: List[str], cuisine_type: str) -> float:
    """Calculate taste/cuisine preference match using embeddings."""
    if not user_preferences:
        return 100.0

    # Embed user preferences
    pref_embeddings = [embeddings.embed_query(pref) for pref in user_preferences]
    centroid = np.mean(pref_embeddings, axis=0)

    # Calculate cosine similarity
    similarity = cosine_similarity(
        dish_embedding.reshape(1, -1),
        centroid.reshape(1, -1)
    )[0][0]

    # Convert similarity (-1 to 1) to score (0 to 100)
    score = (similarity + 1) * 50

    # Bonus for exact cuisine match
    if cuisine_type and cuisine_type.lower() in [p.lower() for p in user_preferences]:
        score = min(score + 10, 100)

    return score

def calculate_habit_alignment(dish_categories: List[str], user_history: List[dict]) -> float:
    """Analyze how dish fits user's ordering patterns."""
    if not user_history:
        return 100.0  # No history = neutral

    # Extract category frequencies from history
    category_counts = {}
    for order in user_history:
        for category in order.get("categories", []):
            category_counts[category] = category_counts.get(category, 0) + 1

    total_orders = len(user_history)

    # Calculate match score
    match_count = 0
    for category in dish_categories:
        if category in category_counts:
            match_count += category_counts[category]

    if total_orders == 0:
        return 100.0

    # Score based on how often user orders similar dishes
    habit_frequency = (match_count / total_orders) * 100
    return habit_frequency

def find_better_alternatives(dish: dict, user_profile: dict, current_score: float) -> List[str]:
    """Find dishes with higher compatibility scores."""
    restaurant_id = dish.get("restaurant_id")

    # Search similar dishes in same restaurant
    similar_dishes = db.dishes.find({
        "restaurant_id": restaurant_id,
        "_id": {"$ne": dish["_id"]}
    }).limit(20)

    alternatives = []
    for candidate in similar_dishes:
        candidate_score = calculate_compatibility(candidate, user_profile)

        if candidate_score.overall_score > current_score + 10:  # At least 10 points better
            alternatives.append({
                "dish_id": candidate["_id"],
                "name": candidate["name"],
                "score": candidate_score.overall_score,
                "improvement": candidate_score.overall_score - current_score
            })

    # Sort by score and return top 3
    alternatives.sort(key=lambda x: x["score"], reverse=True)
    return [a["name"] for a in alternatives[:3]]

def generate_explanation(safety_score, nutrition_score, preference_score, habit_score, dish, user_profile) -> Dict[str, str]:
    """Generate human-readable explanation of scores."""
    explanations = {}

    # Safety explanation
    if safety_score == 100:
        explanations["safety"] = "✅ No allergens detected that match your profile"
    elif safety_score >= 50:
        explanations["safety"] = "⚠️ May contain traces of allergens - verify with restaurant"
    else:
        explanations["safety"] = "❌ Contains allergens you've marked as unsafe"

    # Nutrition explanation
    if nutrition_score >= 80:
        explanations["nutrition"] = "✅ Aligns well with your health goals"
    elif nutrition_score >= 50:
        explanations["nutrition"] = "⚠️ Partially aligns with your health goals"
    else:
        explanations["nutrition"] = "❌ Does not match your nutritional targets"

    # Preference explanation
    if preference_score >= 80:
        explanations["preference"] = "✅ Great match for your taste preferences"
    elif preference_score >= 50:
        explanations["preference"] = "⚠️ Moderate match for your preferences"
    else:
        explanations["preference"] = "❌ May not match your usual taste preferences"

    # Habit explanation
    if habit_score >= 70:
        explanations["habit"] = "✅ Similar to dishes you usually order"
    elif habit_score >= 40:
        explanations["habit"] = "⚠️ Different from your typical choices"
    else:
        explanations["habit"] = "❌ Quite different from your ordering patterns"

    return explanations
```

**API Endpoint**:
```python
# routers/dish_router.py
@router.get("/dishes/{dish_id}/compatibility", response_model=CompatibilityScore)
def get_dish_compatibility(
    dish_id: str,
    user_id: str = Depends(get_current_user_id)
):
    """
    Get compatibility score between dish and user profile.

    Returns multi-dimensional analysis including:
    - Allergen safety
    - Nutritional alignment
    - Taste preference match
    - Ordering habit fit
    """
    dish = dish_service.get_dish(dish_id)
    user = user_service.get_user_by_id(user_id)

    score = compatibility_service.calculate_compatibility(dish, user)
    return score
```

**Frontend Display**:
```jsx
// Dish Card Component
<DishCard>
  <img src={dish.image} />
  <h3>{dish.name}</h3>
  <p>${dish.price}</p>

  {/* UNIQUE FEATURE */}
  <CompatibilityBadge score={dish.compatibilityScore}>
    <div className="score-ring">
      <CircularProgress value={dish.compatibilityScore.overall_score} />
      <span>{dish.compatibilityScore.overall_score}/100</span>
    </div>

    <div className="breakdown">
      <ScoreItem
        icon={<Shield />}
        label="Safety"
        score={dish.compatibilityScore.safety_score}
        status={dish.compatibilityScore.safety_status}
      />
      <ScoreItem
        icon={<Heart />}
        label="Nutrition"
        score={dish.compatibilityScore.nutrition_score}
      />
      <ScoreItem
        icon={<Star />}
        label="Preference"
        score={dish.compatibilityScore.preference_score}
      />
      <ScoreItem
        icon={<TrendingUp />}
        label="Habit Match"
        score={dish.compatibilityScore.habit_score}
      />
    </div>

    {dish.compatibilityScore.alternatives.length > 0 && (
      <Alternatives>
        <p>Better matches for you:</p>
        <ul>
          {dish.compatibilityScore.alternatives.map(alt => (
            <li key={alt}>{alt}</li>
          ))}
        </ul>
      </Alternatives>
    )}
  </CompatibilityBadge>
</DishCard>
```

**Demo Value**:
- ⭐ **Highly Visual**: Color-coded scores, circular progress bars
- 🎯 **AI Transparency**: Shows WHY a dish is recommended
- 🔬 **Explainable AI**: Breaks down the decision-making process
- 💡 **Actionable**: Suggests better alternatives
- 🏆 **Competitive Advantage**: No other food app does this

**Effort**: 15-20 hours

---

### 2. 📸 **Visual Menu Scanning & Instant Allergen Detection** ⭐⭐⭐⭐⭐

**Concept**: Upload a photo of a menu/dish, AI extracts text, identifies dishes, and checks allergen safety in real-time.

**Why It's Unique**:
- Solves real-world problem (physical menus at restaurants)
- Combines OCR + NLP + allergen detection
- Works offline (after initial processing)
- Great for demo/showcase

**How It Works**:
```
User at Restaurant → Takes photo of menu → Uploads
         ↓
[OCR: Extract text from image using Tesseract/Google Vision]
         ↓
[NLP: Parse menu items, prices, descriptions]
         ↓
[LLM: Infer allergens from dish names/descriptions]
         ↓
[Filter: Compare against user allergen profile]
         ↓
Display: Highlighted safe dishes + warnings
```

**Implementation**:
```python
# services/visual_menu_service.py
import pytesseract
from PIL import Image
import re

async def process_menu_image(image_file: UploadFile, user_id: str):
    """
    Process uploaded menu image and extract allergen-safe dishes.

    Steps:
    1. OCR to extract text
    2. Parse menu structure (dishes, prices, descriptions)
    3. Infer allergens using LLM
    4. Filter based on user profile
    5. Return annotated results
    """

    # 1. OCR
    image = Image.open(image_file.file)
    text = pytesseract.image_to_string(image)

    # 2. Parse menu items
    dishes = parse_menu_text(text)

    # 3. Infer allergens for each dish
    for dish in dishes:
        allergens = await infer_allergens_from_text(
            name=dish["name"],
            description=dish.get("description", "")
        )
        dish["inferred_allergens"] = allergens

    # 4. Get user allergen preferences
    user = user_service.get_user_by_id(user_id)
    user_allergens = user.get("allergen_preferences", [])

    # 5. Annotate safety
    for dish in dishes:
        dish["safe_for_user"] = is_safe_for_user(
            dish["inferred_allergens"],
            user_allergens
        )

    return {
        "raw_text": text,
        "dishes": dishes,
        "safe_count": len([d for d in dishes if d["safe_for_user"]]),
        "total_count": len(dishes)
    }

def parse_menu_text(text: str) -> List[dict]:
    """
    Parse OCR text into structured menu items.

    Handles various menu formats:
    - "Dish Name - $12.99 - Description"
    - "Dish Name $12.99\nDescription here"
    - etc.
    """
    lines = text.split("\n")
    dishes = []

    for line in lines:
        # Skip empty lines
        if not line.strip():
            continue

        # Try to extract: name, price, description
        # Pattern: "Name - $XX.XX - Description" or "Name $XX.XX Description"
        price_match = re.search(r'\$(\d+\.?\d*)', line)

        if price_match:
            price = float(price_match.group(1))

            # Everything before price is likely the name
            name_part = line[:price_match.start()].strip(' -')

            # Everything after price is description
            desc_part = line[price_match.end():].strip(' -')

            dishes.append({
                "name": name_part,
                "price": price,
                "description": desc_part if desc_part else ""
            })

    return dishes

async def infer_allergens_from_text(name: str, description: str) -> List[dict]:
    """
    Use LLM to infer allergens from dish name and description.
    """
    prompt = f"""
    Analyze this dish and identify potential allergens.

    Dish Name: {name}
    Description: {description}

    Return a JSON list of allergens with confidence scores:
    [
      {{"allergen": "dairy", "confidence": 0.95, "reasoning": "Contains cheese"}},
      ...
    ]

    Possible allergens: peanuts, tree_nuts, dairy, egg, soy, wheat_gluten, fish, shellfish, sesame
    """

    response = await llm.ainvoke(prompt)
    allergens = json.loads(response.content)
    return allergens
```

**API Endpoint**:
```python
@router.post("/menus/scan", response_model=VisualMenuResult)
async def scan_menu_image(
    image: UploadFile = File(...),
    user_id: str = Depends(get_current_user_id)
):
    """
    Upload a menu image and get allergen analysis.

    Supports: JPG, PNG (max 10MB)
    """
    # Validate file
    if image.content_type not in ["image/jpeg", "image/png"]:
        raise BadRequestException("Only JPG/PNG images allowed")

    result = await visual_menu_service.process_menu_image(image, user_id)
    return result
```

**Frontend**:
```jsx
// Visual Menu Scanner Component
function MenuScanner() {
  const [scanning, setScanning] = useState(false);
  const [result, setResult] = useState(null);

  const handleScan = async (file) => {
    setScanning(true);

    const formData = new FormData();
    formData.append('image', file);

    const response = await fetch('/menus/scan', {
      method: 'POST',
      headers: { 'Authorization': `Bearer ${token}` },
      body: formData
    });

    const data = await response.json();
    setResult(data);
    setScanning(false);
  };

  return (
    <div>
      <h2>Scan Physical Menu</h2>
      <p>Take a photo of a restaurant menu to check allergen safety</p>

      <FileUpload onUpload={handleScan} accept="image/*" />

      {scanning && <Spinner text="Analyzing menu..." />}

      {result && (
        <div>
          <Summary>
            ✅ {result.safe_count} safe dishes out of {result.total_count}
          </Summary>

          <DishList>
            {result.dishes.map(dish => (
              <DishItem
                key={dish.name}
                dish={dish}
                safe={dish.safe_for_user}
              >
                <h3>{dish.name}</h3>
                <p>${dish.price}</p>
                {!dish.safe_for_user && (
                  <Warning>
                    ⚠️ Contains: {dish.inferred_allergens.map(a => a.allergen).join(', ')}
                  </Warning>
                )}
              </DishItem>
            ))}
          </DishList>
        </div>
      )}
    </div>
  );
}
```

**Demo Value**:
- 📱 **Real-world Use Case**: Scan menus at restaurants
- 🎬 **Great for Video Demo**: Very visual, easy to showcase
- 🚀 **Innovative**: Combines multiple AI technologies
- 💯 **Instant Gratification**: Results in seconds

**Effort**: 12-16 hours

---

### 3. 🎤 **Voice-Activated Allergen-Safe Ordering** ⭐⭐⭐⭐

**Concept**: Hands-free ordering using voice commands with real-time allergen verification.

**Why It's Unique**:
- Accessibility feature (helps users with visual impairments)
- Natural interaction (speak naturally, not commands)
- Real-time feedback (voice confirmations)

**How It Works**:
```
User: "Hey SafeBites, find me a nut-free pizza"
         ↓
[Speech-to-Text: Convert audio → text]
         ↓
[Intent Extraction: Parse query]
         ↓
[Semantic Search: Find matching dishes]
         ↓
[Allergen Filter: Remove unsafe options]
         ↓
[Text-to-Speech: "I found 3 nut-free pizzas. Would you like to hear them?"]
         ↓
User: "Yes"
         ↓
[Voice Response: "Option 1: Margherita Pizza, $12.99..."]
```

**Implementation**:
```python
# services/voice_service.py
from google.cloud import speech_v1, texttospeech
import io

async def process_voice_command(audio_file: UploadFile, user_id: str):
    """
    Process voice command for allergen-safe dish search.
    """

    # 1. Speech-to-Text
    text = await speech_to_text(audio_file)

    # 2. Extract intent
    intent = await extract_query_intent(text)

    # 3. Search dishes
    dishes = await semantic_retrieve_with_negation(text, restaurant_id=None)

    # 4. Filter by user allergens
    user = user_service.get_user_by_id(user_id)
    safe_dishes = filter_allergen_safe(dishes, user.allergen_preferences)

    # 5. Generate voice response
    if not safe_dishes:
        response_text = f"Sorry, I couldn't find any {text} that match your dietary needs."
    else:
        response_text = f"I found {len(safe_dishes)} options. "
        response_text += f"The top choice is {safe_dishes[0].dish['name']} "
        response_text += f"for ${safe_dishes[0].dish['price']}. "
        response_text += "Would you like to add it to your cart?"

    # 6. Text-to-Speech
    audio_response = await text_to_speech(response_text)

    return {
        "transcribed_text": text,
        "results": safe_dishes,
        "response_text": response_text,
        "audio_response": audio_response  # Base64 encoded audio
    }

async def speech_to_text(audio_file: UploadFile) -> str:
    """Convert speech to text using Google Cloud Speech API."""
    client = speech_v1.SpeechClient()

    content = await audio_file.read()
    audio = speech_v1.RecognitionAudio(content=content)

    config = speech_v1.RecognitionConfig(
        encoding=speech_v1.RecognitionConfig.AudioEncoding.LINEAR16,
        sample_rate_hertz=16000,
        language_code="en-US",
    )

    response = client.recognize(config=config, audio=audio)

    transcript = ""
    for result in response.results:
        transcript += result.alternatives[0].transcript

    return transcript

async def text_to_speech(text: str) -> bytes:
    """Convert text to speech using Google Cloud TTS."""
    client = texttospeech.TextToSpeechClient()

    synthesis_input = texttospeech.SynthesisInput(text=text)

    voice = texttospeech.VoiceSelectionParams(
        language_code="en-US",
        ssml_gender=texttospeech.SsmlVoiceGender.NEUTRAL
    )

    audio_config = texttospeech.AudioConfig(
        audio_encoding=texttospeech.AudioEncoding.MP3
    )

    response = client.synthesize_speech(
        input=synthesis_input,
        voice=voice,
        audio_config=audio_config
    )

    return response.audio_content
```

**Frontend**:
```jsx
function VoiceSearch() {
  const [recording, setRecording] = useState(false);
  const [processing, setProcessing] = useState(false);

  const startRecording = async () => {
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    const mediaRecorder = new MediaRecorder(stream);

    const audioChunks = [];
    mediaRecorder.ondataavailable = (event) => {
      audioChunks.push(event.data);
    };

    mediaRecorder.onstop = async () => {
      const audioBlob = new Blob(audioChunks, { type: 'audio/wav' });
      await sendVoiceCommand(audioBlob);
    };

    mediaRecorder.start();
    setRecording(true);

    // Auto-stop after 10 seconds
    setTimeout(() => {
      mediaRecorder.stop();
      setRecording(false);
    }, 10000);
  };

  const sendVoiceCommand = async (audioBlob) => {
    setProcessing(true);

    const formData = new FormData();
    formData.append('audio', audioBlob);

    const response = await fetch('/voice/command', {
      method: 'POST',
      body: formData
    });

    const data = await response.json();

    // Play audio response
    const audio = new Audio(`data:audio/mp3;base64,${data.audio_response}`);
    audio.play();

    // Show visual results
    setResults(data.results);
    setProcessing(false);
  };

  return (
    <div>
      <button onClick={startRecording} disabled={recording}>
        {recording ? '🎤 Listening...' : '🎤 Press to Speak'}
      </button>
      {processing && <p>Processing your request...</p>}
    </div>
  );
}
```

**Demo Value**:
- 🎙️ **Interactive Demo**: Live voice interaction
- ♿ **Accessibility**: Helps visually impaired users
- 🌟 **Futuristic**: Voice-first interface
- 📈 **Trending**: Voice commerce is growing

**Effort**: 10-15 hours

---

### 4. 🧬 **Personalized "Allergy Risk Heatmap"** ⭐⭐⭐⭐

**Concept**: Visual heatmap showing allergen risk levels across menu categories/restaurants.

**Why It's Unique**:
- Data visualization of allergen data
- Helps users make informed choices
- Identifies "safe zones" in menus
- Can show trends over time

**Visualization**:
```
Restaurant Menu Categories:

[Appetizers]  [Main Course]  [Desserts]  [Beverages]
   🟢              🟡            🔴          🟢
  Safe         Moderate      High Risk    Safe
  (95%)         (60%)         (10%)      (100%)


Dish-Level Heatmap:
Caesar Salad      ████████░░  80% safe (dairy concern)
Grilled Chicken   ██████████ 100% safe
Chocolate Cake    ██░░░░░░░░  20% safe (nuts, dairy, eggs)
```

**Implementation**:
```python
# services/heatmap_service.py
def generate_allergen_heatmap(restaurant_id: str, user_id: str):
    """
    Generate allergen safety heatmap for restaurant menu.
    """
    user = user_service.get_user_by_id(user_id)
    user_allergens = user.get("allergen_preferences", [])

    dishes = list(db.dishes.find({"restaurant_id": restaurant_id}))

    # Group by category
    categories = {}
    for dish in dishes:
        category = dish.get("category", "Other")
        if category not in categories:
            categories[category] = []

        # Calculate safety score
        safety_score = calculate_dish_safety(dish, user_allergens)
        categories[category].append({
            "name": dish["name"],
            "safety_score": safety_score
        })

    # Calculate category averages
    heatmap = {}
    for category, items in categories.items():
        avg_safety = np.mean([item["safety_score"] for item in items])
        heatmap[category] = {
            "average_safety": avg_safety,
            "risk_level": get_risk_level(avg_safety),
            "dish_count": len(items),
            "dishes": sorted(items, key=lambda x: x["safety_score"], reverse=True)
        }

    return heatmap

def get_risk_level(safety_score: float) -> str:
    """Convert safety score to risk level."""
    if safety_score >= 80:
        return "LOW"
    elif safety_score >= 50:
        return "MODERATE"
    else:
        return "HIGH"
```

**Frontend Visualization**:
```jsx
import { HeatMap } from '@nivo/heatmap';

function AllergenHeatmap({ restaurantId }) {
  const [heatmapData, setHeatmapData] = useState(null);

  useEffect(() => {
    fetch(`/restaurants/${restaurantId}/allergen-heatmap`)
      .then(res => res.json())
      .then(data => setHeatmapData(data));
  }, [restaurantId]);

  return (
    <div>
      <h2>Allergen Safety Overview</h2>

      <HeatMap
        data={formatDataForHeatmap(heatmapData)}
        keys={['safety_score']}
        indexBy="category"
        colors={{
          scheme: 'red_yellow_green',
          type: 'sequential'
        }}
        axisTop={{
          legend: 'Menu Categories',
          legendPosition: 'middle'
        }}
        axisLeft={{
          legend: 'Safety Score',
          legendPosition: 'middle'
        }}
      />

      <Legend>
        <div className="low-risk">🟢 Low Risk (80-100%)</div>
        <div className="moderate-risk">🟡 Moderate Risk (50-79%)</div>
        <div className="high-risk">🔴 High Risk (0-49%)</div>
      </Legend>
    </div>
  );
}
```

**Demo Value**:
- 📊 **Data Visualization**: Beautiful charts
- 🧠 **Insight Generation**: Helps users understand patterns
- 🎨 **Visual Impact**: Great for presentations
- 📈 **Scalable**: Can show multiple restaurants

**Effort**: 8-12 hours

---

### 5. 🔔 **Proactive Allergen Alerts & Menu Change Notifications** ⭐⭐⭐⭐

**Concept**: Real-time notifications when favorite restaurants update menus or add allergen-safe dishes.

**Why It's Unique**:
- Proactive (not reactive)
- Builds user engagement
- Solves real problem (menu items change frequently)
- Can integrate with push notifications

**How It Works**:
```
Restaurant updates menu → Add new "Gluten-Free Pizza"
         ↓
System detects new dish
         ↓
Check users with gluten allergies
         ↓
Send push notification:
"🎉 Good news! Your favorite restaurant 'Pizza Palace' just added a new gluten-free option!"
         ↓
User clicks → Opens app → Sees new dish
```

**Implementation**:
```python
# services/notification_service.py
from datetime import datetime, timedelta

async def check_menu_changes():
    """
    Background task to detect menu changes and notify users.
    Run every hour.
    """
    one_hour_ago = datetime.utcnow() - timedelta(hours=1)

    # Find recently added dishes
    new_dishes = db.dishes.find({
        "created_at": {"$gte": one_hour_ago}
    })

    for dish in new_dishes:
        # Find users who might be interested
        interested_users = find_interested_users(dish)

        for user in interested_users:
            await send_notification(
                user_id=user["_id"],
                title="New Dish Alert!",
                message=f"{dish['name']} was just added to {get_restaurant_name(dish['restaurant_id'])}",
                dish_id=dish["_id"]
            )

def find_interested_users(dish: dict) -> List[dict]:
    """
    Find users who might be interested in this dish.

    Criteria:
    - Users who have favorited this restaurant
    - Users whose allergen preferences make this dish safe
    - Users who have ordered similar dishes before
    """
    restaurant_id = dish["restaurant_id"]

    # Get dish allergens
    dish_allergens = [a["allergen"] for a in dish.get("inferred_allergens", [])]

    # Find users with:
    # 1. This restaurant in favorites
    # 2. Allergen preferences that don't conflict with dish
    users = db.users.find({
        "favorite_restaurants": restaurant_id,
        "allergen_preferences": {"$nin": dish_allergens}
    })

    return list(users)

async def send_notification(user_id: str, title: str, message: str, dish_id: str):
    """Send push notification to user."""
    # Store notification in database
    db.notifications.insert_one({
        "user_id": user_id,
        "title": title,
        "message": message,
        "dish_id": dish_id,
        "created_at": datetime.utcnow(),
        "read": False
    })

    # Send push notification (via Firebase, OneSignal, etc.)
    await push_notification_provider.send({
        "user_id": user_id,
        "title": title,
        "body": message,
        "data": {"dish_id": dish_id}
    })
```

**API Endpoints**:
```python
@router.get("/notifications", response_model=List[Notification])
def get_user_notifications(
    user_id: str = Depends(get_current_user_id),
    unread_only: bool = False
):
    """Get user notifications."""
    query = {"user_id": user_id}
    if unread_only:
        query["read"] = False

    notifications = db.notifications.find(query).sort("created_at", -1).limit(50)
    return list(notifications)

@router.patch("/notifications/{notification_id}/read")
def mark_notification_read(notification_id: str):
    """Mark notification as read."""
    db.notifications.update_one(
        {"_id": ObjectId(notification_id)},
        {"$set": {"read": True}}
    )
    return {"status": "ok"}

@router.post("/users/favorite-restaurants/{restaurant_id}")
def add_favorite_restaurant(
    restaurant_id: str,
    user_id: str = Depends(get_current_user_id)
):
    """Add restaurant to user favorites (for notifications)."""
    db.users.update_one(
        {"_id": ObjectId(user_id)},
        {"$addToSet": {"favorite_restaurants": restaurant_id}}
    )
    return {"status": "ok"}
```

**Frontend**:
```jsx
function NotificationBell() {
  const [notifications, setNotifications] = useState([]);
  const [unreadCount, setUnreadCount] = useState(0);

  useEffect(() => {
    fetchNotifications();

    // Poll for new notifications every minute
    const interval = setInterval(fetchNotifications, 60000);
    return () => clearInterval(interval);
  }, []);

  const fetchNotifications = async () => {
    const response = await fetch('/notifications?unread_only=true');
    const data = await response.json();
    setNotifications(data);
    setUnreadCount(data.length);
  };

  return (
    <div className="notification-bell">
      <button onClick={() => setShowNotifications(!showNotifications)}>
        🔔
        {unreadCount > 0 && <Badge>{unreadCount}</Badge>}
      </button>

      {showNotifications && (
        <NotificationDropdown>
          {notifications.map(notif => (
            <NotificationItem key={notif._id} notification={notif} />
          ))}
        </NotificationDropdown>
      )}
    </div>
  );
}
```

**Demo Value**:
- 🔔 **Engagement**: Brings users back to app
- 🎯 **Personalized**: Tailored to user preferences
- 💡 **Smart**: Uses AI to determine relevance
- 📱 **Mobile-First**: Great for mobile demo

**Effort**: 10-12 hours

---

## 🏆 Recommendation: Pick One for Maximum Impact

For a **showcase/demo**, I recommend:

### **#1: AI-Powered Meal Compatibility Score**

**Why?**
✅ Highly visual and interactive
✅ Demonstrates AI explainability (hot topic)
✅ Unique to SafeBites (no competitors do this)
✅ Easy to understand in a demo
✅ Shows technical depth (multi-factor analysis, embeddings, LLM)
✅ Solves real user pain point (decision paralysis)

**Demo Script**:
1. "Let me show you our unique compatibility scoring system"
2. Open dish page → Show 75/100 score with breakdown
3. "See how it analyzes 4 dimensions: safety, nutrition, preference, and habits"
4. "The AI even suggests better alternatives with 92% compatibility"
5. "This helps users make informed decisions while maintaining transparency"

**Combination Idea**:
Implement **#1 (Compatibility Score)** as primary feature, then add **#4 (Heatmap)** as a complementary visualization. Total effort: ~25 hours.

---

## 📊 Comparison Matrix

| Feature | Impact | Effort | Demo Value | Uniqueness | Technical Depth |
|---------|--------|--------|-----------|------------|-----------------|
| Compatibility Score | ⭐⭐⭐⭐⭐ | 15-20h | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ |
| Visual Menu Scanning | ⭐⭐⭐⭐⭐ | 12-16h | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ |
| Voice Ordering | ⭐⭐⭐⭐ | 10-15h | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ |
| Allergen Heatmap | ⭐⭐⭐⭐ | 8-12h | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐ |
| Proactive Alerts | ⭐⭐⭐⭐ | 10-12h | ⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐ |

---

## 🚀 Quick Start: Implementing Compatibility Score

Want to get started? Here's a minimal viable implementation:

```bash
# 1. Create new files
touch backend/app/models/compatibility_model.py
touch backend/app/services/compatibility_service.py

# 2. Add route
# Edit backend/app/routers/dish_router.py

# 3. Test
pytest backend/app/tests/unit/test_compatibility_service.py

# 4. Frontend component
# Create frontend/src/components/CompatibilityBadge.jsx
```

Good luck with your showcase! 🎉
