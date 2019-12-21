{% if type == 'pending' %} 
{% if updates %} 
*{{nameSocialNetwork}}* ({{socialTime}}) 
{% for text, link, pos in updates %} {{ pos}}) {{ text | truncate(50, True)}}
{% endfor %} {% else %} *{{nameSocialNetwork}}* {% endif %} {% else %} 
{% if updates %} *{{nameSocialNetwork}}*
{% for text, link, pos in updates %} {{ pos}}) {{ text | truncate(40, True)}} {{ stats }}
{% endfor %}
{% else %} *{{nameSocialNetwork}}* {% endif %} {% endif %}

