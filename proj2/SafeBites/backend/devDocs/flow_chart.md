No worries at all! You don't need to know how to code to understand these diagrams.

Think of these flowcharts as a **map for a robot waiter's brain**. They show exactly what steps the AI takes from the moment you say "Hello" to the moment it gives you an answer.

Here is a breakdown of the three processes using simple, real-world analogies.

---

### 1. The "Big Picture" (Top Diagram: Complete Chatbot Flowgraph)

This is the **Main Brain**. Its job is to listen to you, figure out what you want, and delegate the task to the right department.

-   **Start & Query:** You type a message (e.g., "Do you have any vegan pasta?").
-   **Context Resolver:** The AI checks your previous messages. (e.g., Did you just mention you have a peanut allergy? It needs to remember that).
-   **Intent Classifier (The Decision Maker):** This is the most important step. The AI decides: "Is the user asking for a **Menu**?" or "Is the user asking for **Information**?"
-   **Query Part Generator:** It cleans up your question to make it easier for the database to search.
-   **The Split (The Two Paths):**
    -   **Menu Retriever:** If you asked for food recommendations, it goes here.
    -   **Informative Retriever:** If you asked a specific question (like "Is it spicy?" or "What are your hours?"), it goes here.
-   **Response Formatter:** Once the AI finds the answer, this step turns the raw data into a polite, human-like sentence to send back to you.

---

### 2. Finding Food (Middle Diagram: Menu Retriever)

This process runs when the Main Brain decides you are looking for food options. Think of this as the **Menu Specialist**.

-   **Semantic Data Retrieval:** This is a fancy way of saying "Search by Meaning," not just keywords.
    -   _Example:_ If you search for "something healthy," it might find a "Quinoa Salad" even if the word "healthy" isn't in the name. It understands the _concept_ of healthy.
-   **Apply Filters:** It narrows down the list based on hard rules. (e.g., remove anything that costs more than $20, or remove anything with meat).
-   **Retrieved Data Validator:** A final quality check to make sure the food items found actually exist and the data isn't corrupted.

---

### 3. Getting Details (Bottom Diagram: Dish Info Retriever)

This process runs when you have a specific question. Think of this as the **Chef or Customer Service Rep**.

-   **Query Intent Deriver:** It looks at your specific question and splits again:
    -   **Path A (Red Line): General Knowledge.** This is for questions like "What is the capital of France?" or "Tell me a joke." The **General Query Handler** answers this using its basic AI training.
    -   **Path B (Grey Line): Dish Info.** This is for questions like "What ingredients are in the burger?"
-   **Dish Info Query Handler:** It prepares to look up specific facts about a dish.
-   **Semantic Data Retrieval & Filters:** Just like the menu search, it looks for the specific data (ingredients, allergens, calories) and filters out irrelevant stuff.
-   **Information Generator:** It takes the facts (e.g., "Contains: Peanuts, Gluten") and writes an answer for you.

### Summary for a Non-Tech Person:

1.  **Top Chart:** The manager who greets you and decides who you need to talk to.
2.  **Middle Chart:** The waiter who brings you the menu based on what you're craving.
3.  **Bottom Chart:** The chef who answers specific questions about ingredients or general chat.

**Would you like me to explain any of the specific terms like "Semantic Data" or "Context" in more detail?**
