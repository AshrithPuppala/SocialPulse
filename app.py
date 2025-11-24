from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import os
import json
import google.generativeai as genai
from datetime import datetime

app = Flask(__name__, static_folder='templates', static_url_path='')
CORS(app)

# Configure Gemini API
genai.configure(api_key=os.environ.get('GEMINI_API_KEY'))

def analyze_topic_with_gemini(topic, depth='medium'):
    """Use Gemini to analyze public sentiment on a topic"""
    
    try:
        model = genai.GenerativeModel('gemini-2.0-flash-exp')
        
        prompt = f"""You are a social sentiment analyst. Analyze public opinion about: "{topic}"

Based on your knowledge of public discourse, social media trends, news coverage, and general sentiment:

1. Provide a percentage breakdown of sentiment:
   - What % of people have POSITIVE views
   - What % of people have NEGATIVE views  
   - What % are NEUTRAL/UNDECIDED

2. Generate 5 realistic examples of POSITIVE perspectives people would express
3. Generate 5 realistic examples of NEGATIVE perspectives people would express

Format your response as JSON:
{{
  "sentiment_distribution": {{
    "positive": <number between 0-100>,
    "negative": <number between 0-100>,
    "neutral": <number between 0-100>
  }},
  "positive_examples": [
    {{"text": "example quote", "reasoning": "why people think this"}},
    ...5 total
  ],
  "negative_examples": [
    {{"text": "example quote", "reasoning": "why people think this"}},
    ...5 total
  ],
  "analysis_summary": "brief 2-3 sentence summary of the overall sentiment landscape"
}}

Make the percentages add up to 100. Make examples sound like real people talking (casual, authentic). Base this on actual public sentiment trends you're aware of."""

        response = model.generate_content(prompt)
        
        # Parse the response
        response_text = response.text.strip()
        
        # Extract JSON from markdown code blocks if present
        if '```json' in response_text:
            response_text = response_text.split('```json')[1].split('```')[0].strip()
        elif '```' in response_text:
            response_text = response_text.split('```')[1].split('```')[0].strip()
        
        result = json.loads(response_text)
        return result
        
    except Exception as e:
        print(f"Gemini API Error: {str(e)}")
        raise

def format_response(topic, gemini_data):
    """Format Gemini response into our standard format"""
    
    # Convert examples to our format
    positive_examples = []
    for i, ex in enumerate(gemini_data['positive_examples']):
        positive_examples.append({
            'text': ex['text'],
            'sentiment': 'positive',
            'score': 100 - (i * 15),  # Simulate decreasing popularity
            'type': 'opinion',
            'author': f'user_{i+1}',
            'created': datetime.now().strftime('%Y-%m-%d'),
            'reasoning': ex.get('reasoning', '')
        })
    
    negative_examples = []
    for i, ex in enumerate(gemini_data['negative_examples']):
        negative_examples.append({
            'text': ex['text'],
            'sentiment': 'negative',
            'score': 95 - (i * 15),
            'type': 'opinion',
            'author': f'user_{i+6}',
            'created': datetime.now().strftime('%Y-%m-%d'),
            'reasoning': ex.get('reasoning', '')
        })
    
    sentiment_dist = gemini_data['sentiment_distribution']
    
    result = {
        'topic': topic,
        'total_analyzed': 'AI Analysis',
        'posts_analyzed': 'Multiple Sources',
        'sentiment_distribution': {
            'positive': sentiment_dist['positive'],
            'negative': sentiment_dist['negative'],
            'neutral': sentiment_dist['neutral']
        },
        'positive_perspective': {
            'percentage': sentiment_dist['positive'],
            'count': f"{sentiment_dist['positive']}%",
            'examples': positive_examples
        },
        'negative_perspective': {
            'percentage': sentiment_dist['negative'],
            'count': f"{sentiment_dist['negative']}%",
            'examples': negative_examples
        },
        'neutral_count': f"{sentiment_dist['neutral']}%",
        'analysis_summary': gemini_data.get('analysis_summary', ''),
        'timestamp': datetime.now().isoformat(),
        'powered_by': 'Gemini 2.0 Flash'
    }
    
    return result

@app.route('/')
def home():
    return send_from_directory('templates', 'index.html')

@app.route('/api/analyze', methods=['POST'])
def analyze_topic():
    try:
        data = request.get_json()
        topic = data.get('topic', '')
        
        if not topic:
            return jsonify({'error': 'Topic is required'}), 400
        
        if not os.environ.get('GEMINI_API_KEY'):
            return jsonify({'error': 'GEMINI_API_KEY not configured'}), 500
        
        # Use Gemini to analyze the topic
        gemini_data = analyze_topic_with_gemini(topic)
        
        # Format the response
        result = format_response(topic, gemini_data)
        
        return jsonify(result)
    
    except json.JSONDecodeError as e:
        return jsonify({'error': f'Failed to parse AI response: {str(e)}'}), 500
    except Exception as e:
        return jsonify({'error': f'Analysis failed: {str(e)}'}), 500

@app.route('/health', methods=['GET'])
def health_check():
    has_api_key = bool(os.environ.get('GEMINI_API_KEY'))
    return jsonify({
        'status': 'healthy',
        'gemini_configured': has_api_key
    }), 200

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
