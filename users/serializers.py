from django.contrib.auth import get_user_model
from rest_framework import serializers

User = get_user_model()

class signupserializers(serializers.ModelSerializer):

    email = serializers.EmailField(required = True)
    password = serializers.CharField(required = True , min_length=6, max_length=12)


    class Meta:
        model = User
        fields = ("email","password")


    def validate_email(self,value):
        value = value.strip().lower()
        if User.objects.filter(email = value).exists():
            raise serializers.ValidationError("Email already exist")
        return value
    


    def create(self, validated_data):
        email = validated_data["email"].strip().lower()

        user = User.objects.create_user(
            username = email,
            email = email,
            password = validated_data["password"],
        )


        return user
        





