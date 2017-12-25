{% if type == 'pending' %}
{% if updates %}
*{{nameSocialNetwork}}* ({{updates[0][2]}})
{% for text, link, stats in updates %} {{ loop.index0 }}) {{ text | truncate(30, True)}}
{% endfor %}
{% else %}
*{{nameSocialNetwork}}*
{% endif %}
{% else %}
{% if updates %}
*{{nameSocialNetwork}}*
{% for text, link, stats in updates %} {{ loop.index0 }}) {{ text | truncate(25, True)}} ({{ stats }} clicks)
{% endfor %}
{% else %}
*{{nameSocialNetwork}}*
{% endif %}
{% endif %}
