{% if type == 'pending' %} 
{% if updates %} 
*{{nameSocialNetwork}}* ({{socialTime}}) 
{% for text, link, stats in updates %}     {{ loop.index0 }}) {{ text | truncate(30, True)}}
{% endfor %} {% else %} *{{nameSocialNetwork}}* {% endif %} {% else %} 
{% if updates %} *{{nameSocialNetwork}}*
{% for text, link, stats in updates %} {{ text | truncate(40, True)}} {{ stats }}
{% endfor %}
{% else %} *{{nameSocialNetwork}}* {% endif %} {% endif %}

