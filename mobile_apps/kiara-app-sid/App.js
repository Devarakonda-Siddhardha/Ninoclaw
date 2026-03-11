import React, { useState } from 'react';
import { StyleSheet, Text, View, Image, ScrollView, TouchableOpacity, SafeAreaView, Dimensions, StatusBar } from 'react-native';
import { Ionicons } from '@expo/vector-icons';

const { width } = Dimensions.get('window');

const KiaraApp = () => {
  const [activeTab, setActiveTab] = useState('Home');

  const kiaraImages = [
    { id: '1', url: 'http://localhost:8080/builds-assets/tg_8226764849_fcffe869bab6.jpg', title: 'Manish Malhotra Red' },
    { id: '2', url: 'http://localhost:8080/builds-assets/tg_8226764849_fcffe869bab6.jpg', title: 'Stunning Look' },
    { id: '3', url: 'http://localhost:8080/builds-assets/tg_8226764849_fcffe869bab6.jpg', title: 'Elegance' },
  ];

  const renderContent = () => {
    switch (activeTab) {
      case 'Home':
        return (
          <ScrollView showsVerticalScrollIndicator={false}>
            <View style={styles.header}>
              <Text style={styles.headerTitle}>Kiara Advani</Text>
              <Text style={styles.headerSubtitle}>Official Fan App</Text>
            </View>
            
            <View style={styles.featuredContainer}>
              <Image 
                source={{ uri: 'http://localhost:8080/builds-assets/tg_8226764849_fcffe869bab6.jpg' }} 
                style={styles.featuredImage} 
                resizeMode="cover"
              />
              <View style={styles.featuredOverlay}>
                <Text style={styles.featuredText}>Manish Malhotra Collection</Text>
              </View>
            </View>

            <View style={styles.sectionHeader}>
              <Text style={styles.sectionTitle}>Gallery</Text>
              <TouchableOpacity>
                <Text style={styles.seeAll}>See All</Text>
              </TouchableOpacity>
            </View>

            <ScrollView horizontal showsHorizontalScrollIndicator={false} style={styles.galleryScroll}>
              {kiaraImages.map((item) => (
                <View key={item.id} style={styles.galleryItem}>
                  <Image source={{ uri: item.url }} style={styles.galleryImage} />
                  <Text style={styles.galleryText}>{item.title}</Text>
                </View>
              ))}
            </ScrollView>

            <View style={styles.bioContainer}>
              <Text style={styles.sectionTitle}>About Kiara</Text>
              <Text style={styles.bioText}>
                Kiara Advani is one of India's most popular actresses, known for her versatile roles in Bollywood. She made her debut with Fugly and rose to fame with MS Dhoni: The Untold Story and Kabir Singh.
              </Text>
            </View>
            
            <View style={{ height: 100 }} />
          </ScrollView>
        );
      case 'Gallery':
        return (
          <View style={styles.centerContent}>
            <Text style={styles.placeholderText}>Gallery Content Coming Soon</Text>
          </View>
        );
      case 'Profile':
        return (
          <View style={styles.centerContent}>
            <Text style={styles.placeholderText}>Profile Content Coming Soon</Text>
          </View>
        );
      default:
        return null;
    }
  };

  return (
    <SafeAreaView style={styles.container}>
      <StatusBar barStyle="dark-content" />
      
      {renderContent()}

      <View style={styles.tabBar}>
        <TouchableOpacity 
          style={styles.tabItem} 
          onPress={() => setActiveTab('Home')}
        >
          <Ionicons 
            name={activeTab === 'Home' ? 'home' : 'home-outline'} 
            size={24} 
            color={activeTab === 'Home' ? '#E91E63' : '#888'} 
          />
          <Text style={[
            styles.tabLabel, 
            { color: activeTab === 'Home' ? '#E91E63' : '#888' }
          ]}>Home</Text>
        </TouchableOpacity>

        <TouchableOpacity 
          style={styles.tabItem} 
          onPress={() => setActiveTab('Gallery')}
        >
          <Ionicons 
            name={activeTab === 'Gallery' ? 'images' : 'images-outline'} 
            size={24} 
            color={activeTab === 'Gallery' ? '#E91E63' : '#888'} 
          />
          <Text style={[
            styles.tabLabel, 
            { color: activeTab === 'Gallery' ? '#E91E63' : '#888' }
          ]}>Gallery</Text>
        </TouchableOpacity>

        <TouchableOpacity 
          style={styles.tabItem} 
          onPress={() => setActiveTab('Profile')}
        >
          <Ionicons 
            name={activeTab === 'Profile' ? 'person' : 'person-outline'} 
            size={24} 
            color={activeTab === 'Profile' ? '#E91E63' : '#888'} 
          />
          <Text style={[
            styles.tabLabel, 
            { color: activeTab === 'Profile' ? '#E91E63' : '#888' }
          ]}>Profile</Text>
        </TouchableOpacity>
      </View>
    </SafeAreaView>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#FAFAFA',
  },
  header: {
    padding: 20,
    paddingTop: 10,
    backgroundColor: '#fff',
    borderBottomWidth: 1,
    borderBottomColor: '#E0E0E0',
  },
  headerTitle: {
    fontSize: 28,
    fontWeight: 'bold',
    color: '#333',
  },
  headerSubtitle: {
    fontSize: 14,
    color: '#888',
    marginTop: 4,
  },
  featuredContainer: {
    margin: 15,
    borderRadius: 15,
    overflow: 'hidden',
    elevation: 4,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.2,
    shadowRadius: 8,
  },
  featuredImage: {
    width: '100%',
    height: 220,
  },
  featuredOverlay: {
    position: 'absolute',
    bottom: 0,
    left: 0,
    right: 0,
    backgroundColor: 'rgba(0,0,0,0.5)',
    padding: 12,
  },
  featuredText: {
    color: '#fff',
    fontSize: 16,
    fontWeight: '600',
  },
  sectionHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingHorizontal: 15,
    marginTop: 15,
    marginBottom: 10,
  },
  sectionTitle: {
    fontSize: 18,
    fontWeight: '700',
    color: '#333',
  },
  seeAll: {
    color: '#E91E63',
    fontSize: 14,
    fontWeight: '600',
  },
  galleryScroll: {
    paddingHorizontal: 15,
  },
  galleryItem: {
    width: 150,
    marginRight: 12,
  },
  galleryImage: {
    width: '100%',
    height: 200,
    borderRadius: 12,
  },
  galleryText: {
    marginTop: 6,
    fontSize: 12,
    color: '#666',
    textAlign: 'center',
  },
  bioContainer: {
    margin: 15,
    padding: 15,
    backgroundColor: '#fff',
    borderRadius: 12,
    elevation: 2,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 1 },
    shadowOpacity: 0.1,
    shadowRadius: 4,
  },
  bioText: {
    fontSize: 14,
    color: '#666',
    lineHeight: 22,
  },
  centerContent: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
  },
  placeholderText: {
    fontSize: 16,
    color: '#999',
  },
  tabBar: {
    flexDirection: 'row',
    backgroundColor: '#fff',
    borderTopWidth: 1,
    borderTopColor: '#E0E0E0',
    paddingBottom: 5,
  },
  tabItem: {
    flex: 1,
    alignItems: 'center',
    paddingVertical: 8,
  },
  tabLabel: {
    fontSize: 12,
    marginTop: 4,
  },
});

export default KiaraApp;
