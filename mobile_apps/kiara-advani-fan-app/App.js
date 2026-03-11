import React from 'react';
import { View, Text, Image, StyleSheet, ScrollView, TouchableOpacity } from 'react-native';
import { NavigationContainer } from '@react-navigation/native';
import { createBottomTabNavigator } from '@react-navigation/bottom-tabs';
import { Ionicons } from '@expo/vector-icons';

// Screens
const HomeScreen = () => (
  <ScrollView style={styles.container}>
    <Image
      source={{ uri: 'https://images.unsplash.com/photo-1616683693504-3ea7e9ad6fec?w=400&h=400&fit=crop' }}
      style={styles.bannerImage}
    />
    <View style={styles.content}>
      <Text style={styles.title}>Welcome to Kiara Advani Fan App! ✨</Text>
      <Text style={styles.subtitle}>Your favorite Bollywood star</Text>

      <View style={styles.section}>
        <Text style={styles.sectionTitle}>About Kiara</Text>
        <Text style={styles.text}>
          Kiara Advani is an Indian actress who primarily works in Hindi films.
          Born on 31 July 1992, she made her acting debut with the Telugu film
          "Lust Stories" (2018). She gained recognition with "Kabir Singh" (2019)
          and has since starred in many successful films.
        </Text>
      </View>

      <View style={styles.section}>
        <Text style={styles.sectionTitle}>Awards</Text>
        <Text style={styles.text}>• Filmfare Award for Best Actress{'\n'}
        • IIFA Award for Best Actress{'\n'}
        • Zee Cine Award for Best Female Debut</Text>
      </View>
    </View>
  </ScrollView>
);

const PhotosScreen = () => (
  <ScrollView style={styles.container}>
    <View style={styles.photoGrid}>
      {[1, 2, 3, 4, 5, 6].map((item) => (
        <View key={item} style={styles.photoPlaceholder}>
          <Ionicons name="image" size={40} color="#ccc" />
          <Text style={styles.photoText}>Photo {item}</Text>
        </View>
      ))}
    </View>
  </ScrollView>
);

const VideosScreen = () => (
  <ScrollView style={styles.container}>
    <View style={styles.content}>
      <Text style={styles.title}>Videos & Clips</Text>

      {['Trailer - Kabir Singh', 'Interview - The Kapil Sharma Show', 'Song - Rataan Lambiyaan', 'Behind the Scenes'].map((video, index) => (
        <TouchableOpacity key={index} style={styles.videoCard}>
          <View style={styles.videoThumbnail}>
            <Ionicons name="play-circle" size={50} color="#FF6B9D" />
          </View>
          <Text style={styles.videoTitle}>{video}</Text>
        </TouchableOpacity>
      ))}
    </View>
  </ScrollView>
);

const AboutScreen = () => (
  <ScrollView style={styles.container}>
    <View style={styles.content}>
      <Text style={styles.title}>About This App</Text>

      <View style={styles.section}>
        <Text style={styles.sectionTitle}>Version</Text>
        <Text style={styles.text}>1.0.0</Text>
      </View>

      <View style={styles.section}>
        <Text style={styles.sectionTitle}>Developed with ❤️</Text>
        <Text style={styles.text}>
          This fan app is built using React Native and Expo.
          It's a tribute to the amazing talent of Kiara Advani.
        </Text>
      </View>

      <View style={styles.section}>
        <Text style={styles.sectionTitle}>Contact</Text>
        <Text style={styles.text}>For suggestions or feedback, reach out!</Text>
      </View>
    </View>
  </ScrollView>
);

const Tab = createBottomTabNavigator();

export default function App() {
  return (
    <NavigationContainer>
      <Tab.Navigator
        screenOptions={({ route }) => ({
          tabBarIcon: ({ focused, color, size }) => {
            let iconName;

            if (route.name === 'Home') {
              iconName = focused ? 'home' : 'home-outline';
            } else if (route.name === 'Photos') {
              iconName = focused ? 'images' : 'images-outline';
            } else if (route.name === 'Videos') {
              iconName = focused ? 'videocam' : 'videocam-outline';
            } else if (route.name === 'About') {
              iconName = focused ? 'information-circle' : 'information-circle-outline';
            }

            return <Ionicons name={iconName} size={size} color={color} />;
          },
          tabBarActiveTintColor: '#FF6B9D',
          tabBarInactiveTintColor: 'gray',
          headerStyle: {
            backgroundColor: '#FF6B9D',
          },
          headerTintColor: '#fff',
          headerTitleStyle: {
            fontWeight: 'bold',
          },
        })}
      >
        <Tab.Screen name="Home" component={HomeScreen} />
        <Tab.Screen name="Photos" component={PhotosScreen} />
        <Tab.Screen name="Videos" component={VideosScreen} />
        <Tab.Screen name="About" component={AboutScreen} />
      </Tab.Navigator>
    </NavigationContainer>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#f5f5f5',
  },
  bannerImage: {
    width: '100%',
    height: 200,
    resizeMode: 'cover',
  },
  content: {
    padding: 20,
  },
  title: {
    fontSize: 24,
    fontWeight: 'bold',
    color: '#333',
    marginBottom: 10,
    textAlign: 'center',
  },
  subtitle: {
    fontSize: 16,
    color: '#666',
    textAlign: 'center',
    marginBottom: 20,
  },
  section: {
    backgroundColor: '#fff',
    padding: 15,
    borderRadius: 10,
    marginBottom: 15,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.1,
    shadowRadius: 4,
    elevation: 3,
  },
  sectionTitle: {
    fontSize: 18,
    fontWeight: 'bold',
    color: '#FF6B9D',
    marginBottom: 10,
  },
  text: {
    fontSize: 14,
    color: '#333',
    lineHeight: 20,
  },
  photoGrid: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    padding: 5,
    justifyContent: 'space-between',
  },
  photoPlaceholder: {
    width: '48%',
    height: 150,
    backgroundColor: '#fff',
    borderRadius: 10,
    marginBottom: 10,
    justifyContent: 'center',
    alignItems: 'center',
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.1,
    shadowRadius: 4,
    elevation: 3,
  },
  photoText: {
    marginTop: 5,
    color: '#666',
    fontSize: 12,
  },
  videoCard: {
    backgroundColor: '#fff',
    borderRadius: 10,
    marginBottom: 15,
    padding: 15,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.1,
    shadowRadius: 4,
    elevation: 3,
  },
  videoThumbnail: {
    width: '100%',
    height: 150,
    backgroundColor: '#f0f0f0',
    borderRadius: 8,
    justifyContent: 'center',
    alignItems: 'center',
    marginBottom: 10,
  },
  videoTitle: {
    fontSize: 16,
    fontWeight: '600',
    color: '#333',
  },
});