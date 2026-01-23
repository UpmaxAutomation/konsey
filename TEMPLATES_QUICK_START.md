# Prompt Templates - Quick Start Guide

## What are Prompt Templates?

Prompt Templates are pre-built, reusable prompts with customizable variables. Instead of writing complex prompts from scratch, you can:
1. Choose a template designed for your use case
2. Fill in the specific details (variables)
3. Get a perfectly formatted prompt ready to send

## How to Use Templates

### Step 1: Open Templates
Click the "📋 Templates" button above the chat input area.

### Step 2: Browse Templates
- **Search**: Type keywords to filter templates
- **Filter by Category**: Click category chips (content, marketing, seo, etc.)
- **Preview**: Click any template to see its full prompt and variables

### Step 3: Fill Variables
1. Select a template from the list
2. The preview pane shows the prompt and variable form
3. Fill in all required fields (marked with variable names)
4. Click "Use Template"

### Step 4: Send to Council
The filled prompt appears in your chat input. Review and click "Send" to get council responses.

## Available Default Templates

### Content Templates
- **Content Brief** - Create comprehensive content briefs
  - Variables: topic, audience, objectives

- **Blog Outline** - Generate detailed blog post structures
  - Variables: title, word_count, audience

### Marketing Templates
- **Ad Copy Generator** - Create 5 ad variations
  - Variables: product, audience, benefit

- **Email Subject Lines** - Generate 10 A/B testable subject lines
  - Variables: campaign_type, topic, audience

- **Product Description** - Write persuasive product copy
  - Variables: product_name, features, target_customer

### SEO Templates
- **SEO Meta Description** - Optimized 150-160 character descriptions
  - Variables: topic, keyword

### Social Media Templates
- **Social Media Post** - Platform-specific engaging posts
  - Variables: platform, topic, tone

### Research Templates
- **Competitor Analysis** - Structured competitive analysis
  - Variables: competitor, industry, our_company, focus_areas

## Creating Custom Templates

### Step 1: Open Create Form
Click "+ Create Template" button at the top of the Templates modal.

### Step 2: Fill Template Details
- **Name**: Descriptive name (e.g., "Product Launch Email")
- **Category**: Choose existing or create new category
- **Prompt Text**: Write your prompt with variables

### Step 3: Add Variables
Use `{{variable_name}}` syntax in your prompt:
```
Write a press release for {{product_name}} targeting {{audience}}.
Key message: {{key_message}}
Launch date: {{launch_date}}
```

Variables are automatically detected and shown below the text area.

### Step 4: Save Template
Click "Create Template" to save. Your template is now available in the list.

## Managing Templates

### Edit Templates
Custom templates can be updated via API (UI editing coming soon).

### Delete Templates
- Custom templates: Click 🗑️ icon on template card
- Default templates: Cannot be deleted (protected)

### Organize Templates
- Use categories to group related templates
- Search to quickly find templates
- Custom templates show alongside defaults

## Tips for Best Results

1. **Be Specific**: Fill variables with detailed information
2. **Use Consistent Tone**: Match variable content to desired output tone
3. **Test & Iterate**: Try different variable values to see what works best
4. **Save Variations**: Create custom templates for frequently used prompts
5. **Leverage Council**: Templates work great with multi-model deliberation

## Example Workflow

### Scenario: Creating Ad Copy

1. Click "📋 Templates"
2. Filter by "marketing" category
3. Select "Ad Copy Generator"
4. Fill variables:
   - product: "AI-powered task manager"
   - audience: "busy professionals aged 25-45"
   - benefit: "save 10 hours per week on task organization"
5. Click "Use Template"
6. Review generated prompt
7. Send to council
8. Get 5 diverse perspectives on ad copy variations

### Result
The council provides multiple creative approaches, each with unique selling angles and copywriting styles.

## Variable Naming Best Practices

When creating custom templates:

- **Use snake_case**: `target_audience` not `Target Audience`
- **Be descriptive**: `key_benefit` not `kb`
- **Group related**: `product_name`, `product_price`, `product_features`
- **Avoid spaces**: Variables cannot contain spaces
- **Use only alphanumeric**: Letters, numbers, and underscores only

## Common Issues

### "Please fill in all variables"
- Ensure every variable field has a value before clicking "Use Template"

### Template doesn't appear
- Check category filter - try clicking "All"
- Clear search box
- Refresh the browser

### Variables not detected
- Ensure you use double curly braces: `{{variable}}`
- Variable names must be alphanumeric + underscores
- No spaces allowed in variable names

## Advanced Usage

### Nested Prompts
Use templates as starting points for complex multi-stage prompts:
1. Fill template with general info
2. Edit the generated prompt to add specifics
3. Send to council

### Combining Templates
Copy-paste filled templates to create hybrid prompts:
1. Fill "Content Brief" template
2. Copy output
3. Fill "Blog Outline" template
4. Combine both in chat input

### Template Chaining
Use council output as variables for next template:
1. Use "Competitor Analysis" template
2. Get council insights
3. Use insights as `{{competitive_advantage}}` in "Ad Copy Generator"

## API Access

For programmatic access to templates:

```bash
# List all templates
GET /api/templates

# Get specific template
GET /api/templates/{template_id}

# Create template
POST /api/templates
{
  "name": "My Template",
  "category": "custom",
  "prompt_text": "Create {{output}} for {{target}}",
  "variables": ["output", "target"]
}

# Fill template
POST /api/templates/{template_id}/fill
{
  "variable_values": {
    "output": "landing page copy",
    "target": "SaaS startups"
  }
}
```

## Support

For issues or questions:
1. Check this guide first
2. Review the main documentation
3. Check API documentation for advanced usage
4. Inspect browser console for errors

## What's Next?

Planned features for future releases:
- Template editing UI
- Template folders/organization
- Template import/export
- Usage analytics
- AI-powered template suggestions
- Template sharing community
- Multi-language support

---

**Happy prompting!** 🚀
