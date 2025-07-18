#!/usr/bin/env python3
"""
Simple test script to test the API with curl.
"""

import requests
import json
import time

def test_api():
    """Test the API with a simple request."""
    
    url = "http://localhost:8000/api/v1/process"
    data = {
        "url": "https://www.instagram.com/reel/DK4xvp2v9hC/"
    }
    
    print("🚀 Testing API with Instagram URL...")
    print(f"URL: {data['url']}")
    print("=" * 50)
    
    try:
        # Make the request with a longer timeout
        response = requests.post(
            url,
            json=data,
            timeout=300,  # 5 minutes timeout
            headers={"Content-Type": "application/json"}
        )
        
        print(f"Status Code: {response.status_code}")
        print(f"Response: {response.text}")
        
        if response.status_code == 200:
            result = response.json()
            print("\n✅ SUCCESS!")
            print(f"Total clips: {result.get('total_clips', 0)}")
            print(f"Processing time: {result.get('processing_time', 0):.2f}s")
            
            # Show clips
            clips = result.get('processed_clips', [])
            if clips:
                print("\n📋 Generated Clips:")
                for i, clip in enumerate(clips, 1):
                    print(f"{i}. {clip.get('exercise_name', 'Unknown')}")
                    print(f"   Duration: {clip.get('total_duration', 0):.1f}s")
                    print(f"   Path: {clip.get('video_path', 'N/A')}")
        else:
            print(f"\n❌ ERROR: {response.status_code}")
            print(response.text)
            
    except requests.exceptions.Timeout:
        print("⏰ Request timed out (5 minutes)")
    except requests.exceptions.ConnectionError:
        print("🔌 Connection error - is the server running?")
    except Exception as e:
        print(f"❌ Error: {str(e)}")

if __name__ == "__main__":
    test_api() 