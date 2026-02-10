# Prompt Templates - Quick Start Guide

## What Are Prompt Templates?

Prompt templates are reusable prompts with variable placeholders that help you quickly generate consistent, high-quality prompts for the LLM Council.

## Quick Start

### 1. Restart Backend (Required - One Time)
```bash
# Find and kill the current backend process
ps aux | grep "python.*backend" | grep -v grep
kill <PID>

# Start backend
cd /Users/sezars/llm-council
python -m backend.main
```

### 2. Access Templates
- Click the **📋 Templates** button in the chat interface
- Browse 8 default templates across different categories

### 3. Use a Template
1. Click any template to preview it
2. Fill in the variables (highlighted fields)
3. Click **"Use Template"**
4. The filled prompt appears in your chat input
5. Edit if needed, then send!

### 4. Create Custom Template
1. Click **"+ Create Template"**
2. Enter name (e.g., "Product Launch Plan")
3. Enter category (e.g., "marketing")
4. Write prompt with `{{variables}}`:
   ```
   Create a launch plan for {{product_name}} targeting {{audience}}.
   Key features: {{features}}
   Launch date: {{date}}
   ```
5. Variables auto-detected and shown
6. Click **"Create Template"**

## Template Syntax

### Variables
Use double curly braces for variables:
```
{{variable_name}}
```

**Examples:**
```
Generate a blog post about {{topic}} for {{audience}}.
```

```
Write {{count}} ad variations for {{product}}.
Focus on: {{benefit}}
```

### Rules
- Variable names: letters, numbers, underscore only
- Case-sensitive
- No spaces in variable names
- Use descriptive names: `{{target_audience}}` not `{{ta}}`

## Default Templates

### Content Creation
- **Content Brief**: Comprehensive content briefs
- **Blog Outline**: Structured blog post outlines

### Marketing
- **Ad Copy Generator**: Multiple ad variations
- **Email Subject Lines**: A/B test subject lines

### SEO
- **SEO Meta Description**: Optimized meta descriptions

### Social Media
- **Social Media Post**: Platform-specific posts

### Research
- **Competitor Analysis**: Detailed competitor analysis

### E-commerce
- **Product Description**: Persuasive product descriptions

## Tips & Tricks

### Best Practices
1. **Be Specific**: Use descriptive variable names
   - Good: `{{target_demographic}}`
   - Bad: `{{td}}`

2. **Provide Context**: Include instructions in the template
   ```
   Create a {{format}} about {{topic}}.
   Target audience: {{audience}}
   Tone: {{tone}}
   Length: {{length}} words
   ```

3. **Use Defaults in Description**: Help users know what to enter
   - Variable name: `word_count` (implies numbers)
   - Variable name: `tone_casual_or_formal` (shows options)

### Common Use Cases

**Weekly Newsletter**:
```
Write a {{day}} newsletter for {{company}}.
This week's topic: {{topic}}
Key announcement: {{announcement}}
CTA: {{call_to_action}}
```

**Product Comparison**:
```
Compare {{product_1}} vs {{product_2}}.
Focus on: {{comparison_points}}
Target buyer: {{buyer_persona}}
```

**Meeting Agenda**:
```
Create a meeting agenda for {{meeting_type}}.
Duration: {{duration}}
Attendees: {{attendees}}
Key topics: {{topics}}
```

## Keyboard Shortcuts

- **Enter** in variable field: Jump to next field
- **Shift + Enter** in prompt: New line
- **Esc**: Close templates modal

## Categories

Organize templates by category:
- `content` - Content creation
- `marketing` - Marketing materials
- `seo` - SEO optimization
- `social` - Social media
- `email` - Email campaigns
- `research` - Research & analysis
- `ecommerce` - E-commerce content
- `custom` - Your category name

## Managing Templates

### Edit Custom Templates
- Click template name
- Modify fields
- Save changes
- (Default templates cannot be edited)

### Delete Custom Templates
- Click 🗑️ icon on custom template
- Confirm deletion
- (Default templates cannot be deleted)

### Search Templates
- Use search box to filter by name or category
- Click category chips to filter
- Click "All" to show all templates

## API Access (Advanced)

### List Templates
```bash
curl http://localhost:8001/api/templates
```

### Get Template
```bash
curl http://localhost:8001/api/templates/{template_id}
```

### Create Template
```bash
curl -X POST http://localhost:8001/api/templates \
  -H "Content-Type: application/json" \
  -d '{
    "name": "My Template",
    "category": "custom",
    "prompt_text": "Your prompt with {{variables}}",
    "variables": ["variables", "list"]
  }'
```

### Fill Template
```bash
curl -X POST http://localhost:8001/api/templates/{id}/fill \
  -H "Content-Type: application/json" \
  -d '{
    "variable_values": {
      "variables": "value1",
      "list": "value2"
    }
  }'
```

## Troubleshooting

**Templates button not visible?**
- Refresh the page
- Check frontend is running on port 5173

**Templates not loading?**
- Restart backend server
- Check backend running on port 8001
- Test with: `curl http://localhost:8001/api/templates`

**Variables not detected?**
- Use double curly braces: `{{variable}}`
- No spaces: `{{var_name}}` not `{{ var_name }}`
- Valid characters: a-z, A-Z, 0-9, _

**Cannot delete template?**
- Only custom templates can be deleted
- Default templates (blue badge) are permanent

## Examples

### Example 1: Blog Post Template
```
Create a comprehensive blog post about {{topic}}.

Target audience: {{target_audience}}
Word count: {{word_count}}
Tone: {{tone}}
SEO keyword: {{primary_keyword}}

Include:
- Introduction with hook
- {{section_count}} main sections
- Conclusion with CTA
- Meta description (150-160 chars)
```

**Variables**: topic, target_audience, word_count, tone, primary_keyword, section_count

### Example 2: Landing Page Template
```
Design a landing page for {{product_name}}.

Value proposition: {{value_proposition}}
Target customer: {{target_customer}}
Main benefit: {{main_benefit}}
Secondary benefits: {{secondary_benefits}}
Price point: {{price}}
CTA: {{call_to_action}}

Include:
- Hero section with headline
- Features comparison table
- Social proof (testimonials)
- Pricing section
- FAQ section
```

**Variables**: product_name, value_proposition, target_customer, main_benefit, secondary_benefits, price, call_to_action

### Example 3: Social Campaign Template
```
Create a {{duration}}-day social media campaign for {{brand}}.

Platform: {{platform}}
Campaign goal: {{goal}}
Target audience: {{audience}}
Hashtags: {{hashtags}}
Posting frequency: {{frequency}}

Deliverables:
- {{post_count}} posts with copy
- Image/video suggestions
- Engagement strategy
- Success metrics
```

**Variables**: duration, brand, platform, goal, audience, hashtags, frequency, post_count

## Ready to Use!

1. ✅ Restart backend (one-time setup)
2. ✅ Click 📋 Templates button
3. ✅ Choose a template
4. ✅ Fill variables
5. ✅ Send to LLM Council

Happy prompting! 🚀
