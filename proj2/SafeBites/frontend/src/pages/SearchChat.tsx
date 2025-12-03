import { useState, useRef, useEffect } from 'react';
import { API_BASE_URL } from '../config/api';
import './SearchChat.css';

interface DishResult {
  dish_id: string;
  dish_name: string;
  description: string;
  price: number;
  ingredients: string[];
  allergens: string[];
  nutrition_facts?: {
    calories?: { value: number; confidence?: number };
    protein?: { value: number; confidence?: number };
    fat?: { value: number; confidence?: number };
    carbohydrates?: { value: number; confidence?: number };
    sugar?: { value: number; confidence?: number };
    fiber?: { value: number; confidence?: number };
  };
  serving_size?: string;
  availaibility?: boolean | null;
}

interface Message {
  id: string;
  type: 'user' | 'assistant';
  content: string;
  timestamp: Date;
  menuResults?: DishResult[];
  infoResults?: any;
}

function SearchChat() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [inputValue, setInputValue] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);

  // Example queries for quick start
  const exampleQueries = [
    "Show me pizza dishes",
    "What dishes contain nuts?",
    "Show me all pasta options",
    "List dishes under $20"
  ];

  // Auto-scroll to bottom when new messages arrive
  useEffect(() => {
    scrollToBottom();
  }, [messages, isLoading]);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  // Handle textarea auto-resize
  const handleInputChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    setInputValue(e.target.value);
    
    // Auto-resize textarea
    e.target.style.height = 'auto';
    e.target.style.height = `${Math.min(e.target.scrollHeight, 120)}px`;
  };

  // Handle Enter key (Shift+Enter for new line)
  const handleKeyPress = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSendMessage();
    }
  };

  const handleSendMessage = async () => {
    if (!inputValue.trim() || isLoading) return;

    const userMessage: Message = {
      id: Date.now().toString(),
      type: 'user',
      content: inputValue.trim(),
      timestamp: new Date()
    };

    setMessages(prev => [...prev, userMessage]);
    const currentQuery = inputValue.trim();
    setInputValue('');
    setIsLoading(true);

    // Reset textarea height
    if (inputRef.current) {
      inputRef.current.style.height = 'auto';
    }

    try {
      // Get user_id from localStorage if logged in
      const user_id = localStorage.getItem("authToken") || undefined;

      // Request body with optional user_id
      const requestBody = {
        query: currentQuery,
        restaurant_id: "rest_1",
        ...(user_id && { user_id }) // Only include user_id if it exists
      };

      console.log('=== CHAT API REQUEST ===');
      console.log('URL:', `${API_BASE_URL}/restaurants/search`);
      console.log('Body:', JSON.stringify(requestBody, null, 2));

      // Call the search API (correct endpoint!)
      const response = await fetch(`${API_BASE_URL}/restaurants/search`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(requestBody)
      });

      console.log('=== CHAT API RESPONSE ===');
      console.log('Status:', response.status);
      console.log('Status Text:', response.statusText);

      // Get the response text first
      const responseText = await response.text();
      console.log('Response Text (first 500 chars):', responseText.substring(0, 500));

      // Try to parse as JSON
      let data;
      try {
        data = JSON.parse(responseText);
        console.log('Parsed JSON:', data);
      } catch (parseError) {
        console.error('Failed to parse response as JSON:', parseError);
        throw new Error(`API returned non-JSON response: ${responseText.substring(0, 200)}`);
      }

      if (!response.ok) {
        console.error('API Error Response:', data);
        throw new Error(
          data.detail || 
          data.message || 
          data.error ||
          `API request failed with status ${response.status}`
        );
      }

      // Process the response
      let assistantContent = '';
      let menuResults: DishResult[] = [];
      let infoResults = null;

      console.log('=== PROCESSING RESPONSE ===');

      // Extract menu results (dishes)
      if (data.menu_results && Object.keys(data.menu_results).length > 0) {
        console.log('Found menu_results:', data.menu_results);
        
        // menu_results is an object with queries as keys
        Object.entries(data.menu_results).forEach(([query, results]: [string, any]) => {
          console.log(`Processing query "${query}":`, results);
          if (Array.isArray(results)) {
            menuResults = [...menuResults, ...results];
          }
        });

        if (menuResults.length > 0) {
          assistantContent = `I found ${menuResults.length} dish${menuResults.length > 1 ? 'es' : ''} matching your search! 🍽️`;
          console.log('Total dishes found:', menuResults.length);
        }
      } else {
        console.log('No menu_results in response');
      }

      // Extract info results (answers to questions)
      if (data.info_results && data.info_results.info_results) {
        console.log('Found info_results:', data.info_results);
        infoResults = data.info_results.info_results;

        // Build response text from info results
        const infoTexts: string[] = [];
        Object.entries(infoResults).forEach(([question, info]: [string, any]) => {
          console.log(`Info for "${question}":`, info);
          if (info.requested_info) {
            infoTexts.push(info.requested_info);
          }
        });

        if (infoTexts.length > 0) {
          if (assistantContent) {
            assistantContent += '\n\n' + infoTexts.join('\n\n');
          } else {
            assistantContent = infoTexts.join('\n\n');
          }
        }
      } else {
        console.log('No info_results in response');
      }

      // Extract user preference results (e.g., "what am I allergic to?")
      if (data.preference_results && data.preference_results.preference_results) {
        console.log('Found preference_results:', data.preference_results);

        // Build response text from preference results
        const prefTexts: string[] = [];
        Object.entries(data.preference_results.preference_results).forEach(([question, pref]: [string, any]) => {
          console.log(`Preference for "${question}":`, pref);
          if (pref.answer) {
            prefTexts.push(pref.answer);
          }
        });

        if (prefTexts.length > 0) {
          if (assistantContent) {
            assistantContent += '\n\n' + prefTexts.join('\n\n');
          } else {
            assistantContent = prefTexts.join('\n\n');
          }
        }
      } else {
        console.log('No preference_results in response');
      }

      // Use the general response if available and no specific results
      if (!assistantContent && data.response) {
        console.log('Using general response field:', data.response);
        assistantContent = data.response;
      }

      // Check status field
      if (data.status) {
        console.log('Response status:', data.status);
      }

      // Fallback if still no content
      if (!assistantContent && menuResults.length === 0) {
        console.log('No content found in response, using fallback message');
        assistantContent = "I couldn't find any results for your query. Could you try rephrasing or ask about specific dishes or dietary preferences?";
      }

      console.log('=== FINAL ASSISTANT MESSAGE ===');
      console.log('Content:', assistantContent);
      console.log('Menu Results Count:', menuResults.length);

      const assistantMessage: Message = {
        id: (Date.now() + 1).toString(),
        type: 'assistant',
        content: assistantContent,
        timestamp: new Date(),
        menuResults: menuResults.length > 0 ? menuResults : undefined,
        infoResults: infoResults
      };

      setMessages(prev => [...prev, assistantMessage]);

    } catch (error: any) {
      console.error('=== ERROR ===');
      console.error('Error details:', error);
      console.error('Error message:', error.message);
      
      let errorContent = 'Sorry, I encountered an error processing your request. ';
      
      // More specific error messages
      if (error.message.includes('Failed to fetch') || error.message.includes('NetworkError')) {
        errorContent += 'Could not connect to the server. Please check your internet connection.';
      } else if (error.message.includes('404')) {
        errorContent += 'The search endpoint was not found. Please contact support.';
      } else if (error.message.includes('500')) {
        errorContent += 'The server encountered an error. The service might be starting up (this can take 30-60 seconds on Render). Please try again in a moment.';
      } else if (error.message.includes('timeout')) {
        errorContent += 'The request timed out. The server might be slow to respond.';
      } else if (error.message.includes('non-JSON')) {
        errorContent += 'The server returned an invalid response format.';
      } else {
        errorContent += `Error: ${error.message}`;
      }
      
      const errorMessage: Message = {
        id: (Date.now() + 1).toString(),
        type: 'assistant',
        content: errorContent,
        timestamp: new Date()
      };
      
      setMessages(prev => [...prev, errorMessage]);
    } finally {
      setIsLoading(false);
    }
  };

  const handleExampleQuery = (query: string) => {
    setInputValue(query);
    inputRef.current?.focus();
  };

  const formatTime = (date: Date) => {
    return date.toLocaleTimeString('en-US', { 
      hour: 'numeric', 
      minute: '2-digit',
      hour12: true 
    });
  };

  return (
    <div className="search-chat-container">
      {/* Header with Instructions */}
      <div className="chat-header">
        <h1 className="chat-title">Search Chat</h1>
        <div className="chat-instructions">
          <h3>How to use:</h3>
          <ul>
            <li>Ask questions in natural language, like <code>"Show me pizza dishes"</code></li>
            <li>Ask about allergens: <code>"Does pizza contain any nuts?"</code></li>
            <li>Set price limits: <code>"Show dishes under $20"</code></li>
            <li>Ask about nutrition: <code>"What are the calories in this dish?"</code></li>
            <li>Combine queries: <code>"Pizza dishes. Also, does pizza contain nuts?"</code></li>
            <li>Press <strong>Enter</strong> to send, <strong>Shift+Enter</strong> for new line</li>
          </ul>
        </div>
      </div>

      {/* Messages Area */}
      <div className="chat-messages-area">
        {messages.length === 0 ? (
          <div className="empty-chat-state">
            <img src="/icons/hugeicon_ai_search.png" alt="Chat" className="empty-chat-icon" />
            <h3>Start a Conversation</h3>
            <p>Ask me anything about the menu, allergens, nutrition, or dietary preferences!</p>
            
            {/* Example Queries */}
            <div className="example-queries">
              {exampleQueries.map((query, index) => (
                <button
                  key={index}
                  className="example-query-btn"
                  onClick={() => handleExampleQuery(query)}
                >
                  {query}
                </button>
              ))}
            </div>
          </div>
        ) : (
          <>
            {messages.map((message) => (
              <div key={message.id} className={`message-wrapper ${message.type}`}>
                <div className={`message-bubble ${message.type}`}>
                  <p className="message-content">{message.content}</p>
                  
                  {/* Render menu results (dishes) if present */}
                  {message.menuResults && message.menuResults.length > 0 && (
                    <div className="results-container">
                      {message.menuResults.map((dish, idx) => (
                        <div key={dish.dish_id || idx} className="result-card">
                          <div className="result-header">
                            <h4 className="result-name">{dish.dish_name}</h4>
                            <span className="result-price">${dish.price.toFixed(2)}</span>
                          </div>
                          
                          <p className="result-description">{dish.description}</p>
                          
                          {/* Serving Size */}
                          {dish.serving_size && (
                            <p className="result-detail">
                              <strong>Serving:</strong> {dish.serving_size}
                            </p>
                          )}
                          
                          {/* Allergens */}
                          {dish.allergens && dish.allergens.length > 0 && (
                            <div className="result-allergens">
                              <strong>Allergens:</strong>
                              <div className="allergen-tags">
                                {dish.allergens.map((allergen, aIdx) => (
                                  <span key={aIdx} className="allergen-tag">
                                    {allergen}
                                  </span>
                                ))}
                              </div>
                            </div>
                          )}
                          
                          {/* Nutrition Facts Preview */}
                          {dish.nutrition_facts && (
                            <div className="result-nutrition">
                              <strong>Nutrition:</strong>{' '}
                              {dish.nutrition_facts.calories && (
                                <span>{dish.nutrition_facts.calories.value} cal</span>
                              )}
                              {dish.nutrition_facts.protein && (
                                <span> • {dish.nutrition_facts.protein.value}g protein</span>
                              )}
                              {dish.nutrition_facts.carbohydrates && (
                                <span> • {dish.nutrition_facts.carbohydrates.value}g carbs</span>
                              )}
                            </div>
                          )}
                        </div>
                      ))}
                    </div>
                  )}
                  
                  <div className="message-timestamp">{formatTime(message.timestamp)}</div>
                </div>
              </div>
            ))}

            {/* Loading Indicator */}
            {isLoading && (
              <div className="loading-wrapper">
                <div className="loading-bubble">
                  <div className="loading-dots">
                    <div className="loading-dot"></div>
                    <div className="loading-dot"></div>
                    <div className="loading-dot"></div>
                  </div>
                  <span className="loading-text">Searching...</span>
                </div>
              </div>
            )}
            
            {/* Auto-scroll anchor */}
            <div ref={messagesEndRef} />
          </>
        )}
      </div>

      {/* Input Bar (Fixed at Bottom) */}
      <div className="chat-input-container">
        <div className="chat-input-wrapper">
          <textarea
            ref={inputRef}
            className="chat-input"
            placeholder="Ask about dishes, allergens, nutrition, or dietary preferences..."
            value={inputValue}
            onChange={handleInputChange}
            onKeyPress={handleKeyPress}
            rows={1}
            disabled={isLoading}
          />
          <button
            className="chat-send-btn"
            onClick={handleSendMessage}
            disabled={!inputValue.trim() || isLoading}
          >
            {isLoading ? 'Sending...' : 'Send'}
            {!isLoading && (
              <img src="/icons/icons8-search-24.png" alt="Send" className="send-icon" />
            )}
          </button>
        </div>
      </div>
    </div>
  );
}

export default SearchChat;