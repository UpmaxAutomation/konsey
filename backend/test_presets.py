"""Test script for council presets functionality."""

import asyncio
import httpx


async def test_presets():
    """Test the presets endpoints."""
    base_url = "http://localhost:8001"

    async with httpx.AsyncClient() as client:
        print("Testing Council Presets Implementation\n")
        print("=" * 50)

        # Test 1: List all presets
        print("\n1. Testing GET /api/presets")
        print("-" * 50)
        response = await client.get(f"{base_url}/api/presets")
        if response.status_code == 200:
            data = response.json()
            print(f"✓ Successfully retrieved {len(data['presets'])} presets:")
            for preset in data["presets"]:
                print(f"  - {preset['id']}: {preset['name']}")
                print(f"    Description: {preset['description']}")
                print(f"    Models: {', '.join(preset['models'])}")
                print(f"    Chairman: {preset['chairman']}")
                print()
        else:
            print(f"✗ Failed with status {response.status_code}: {response.text}")

        # Test 2: Get current config
        print("\n2. Testing GET /api/config (before applying preset)")
        print("-" * 50)
        response = await client.get(f"{base_url}/api/config")
        if response.status_code == 200:
            data = response.json()
            print(f"✓ Current council models: {', '.join(data['council_models'])}")
            print(f"✓ Current chairman: {data['chairman_model']}")
        else:
            print(f"✗ Failed with status {response.status_code}")

        # Test 3: Apply code_review preset
        print("\n3. Testing POST /api/presets/code_review/apply")
        print("-" * 50)
        response = await client.post(f"{base_url}/api/presets/code_review/apply")
        if response.status_code == 200:
            data = response.json()
            print(f"✓ {data['message']}")
            print(f"✓ New council models: {', '.join(data['council_models'])}")
            print(f"✓ New chairman: {data['chairman_model']}")
        else:
            print(f"✗ Failed with status {response.status_code}: {response.text}")

        # Test 4: Verify config changed
        print("\n4. Testing GET /api/config (after applying preset)")
        print("-" * 50)
        response = await client.get(f"{base_url}/api/config")
        if response.status_code == 200:
            data = response.json()
            print(f"✓ Updated council models: {', '.join(data['council_models'])}")
            print(f"✓ Updated chairman: {data['chairman_model']}")
        else:
            print(f"✗ Failed with status {response.status_code}")

        # Test 5: Apply reasoning preset
        print("\n5. Testing POST /api/presets/reasoning/apply")
        print("-" * 50)
        response = await client.post(f"{base_url}/api/presets/reasoning/apply")
        if response.status_code == 200:
            data = response.json()
            print(f"✓ {data['message']}")
            print(f"✓ New council models: {', '.join(data['council_models'])}")
            print(f"✓ New chairman: {data['chairman_model']}")
        else:
            print(f"✗ Failed with status {response.status_code}: {response.text}")

        # Test 6: Try invalid preset
        print("\n6. Testing POST /api/presets/invalid_preset/apply (should fail)")
        print("-" * 50)
        response = await client.post(f"{base_url}/api/presets/invalid_preset/apply")
        if response.status_code == 404:
            print(f"✓ Correctly returned 404 for invalid preset")
            print(f"  Error: {response.json()['detail']}")
        else:
            print(f"✗ Expected 404, got {response.status_code}")

        # Test 7: Reset to defaults
        print("\n7. Testing POST /api/config/reset")
        print("-" * 50)
        response = await client.post(f"{base_url}/api/config/reset")
        if response.status_code == 200:
            data = response.json()
            print(f"✓ Reset to default configuration")
            print(f"✓ Council models: {', '.join(data['council_models'])}")
            print(f"✓ Chairman: {data['chairman_model']}")
        else:
            print(f"✗ Failed with status {response.status_code}")

        print("\n" + "=" * 50)
        print("All tests completed!")
        print("=" * 50)


if __name__ == "__main__":
    print("\nMake sure the backend is running on http://localhost:8001")
    print("Start it with: python -m backend.main\n")
    asyncio.run(test_presets())
