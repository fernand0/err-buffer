{% if type == 'pending' %} 
{% if updates %} 
*{{nameSocialNetwork}}* ({{post}}) 
{% for text, link, pos in updates %} {{ pos}}) {{ text | truncate(50, True)}}
{% endfor %} {% else %} *{{nameSocialNetwork}}* ({{post}}){% endif %} {% else %} 
{% if type == 'longer' %}
{% if updates %} 
*{{nameSocialNetwork}}* ({{post}}) 
{% for text, link, pos in updates %} {{ pos}} {{ text }}
{% endfor %} {% else %} *{{nameSocialNetwork}}* {% endif %} {% else %}
{% if updates %} *{{nameSocialNetwork}}*
{% for text, link, pos in updates %} {{ pos}} {{ text | truncate(40, True)}} {{ stats }}
{% endfor %}
{% else %} *{{nameSocialNetwork}}* {% endif %} *{{nameSocialNetwork}}* {% endif %}
{% endif %}
