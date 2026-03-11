import React from 'react';
import {
  StyleSheet,
  Text,
  View,
  Image,
  ScrollView,
  TouchableOpacity,
  Dimensions,
  SafeAreaView,
  StatusBar,
} from 'react-native';

const { width } = Dimensions.get('window');

export default function App() {
  return (
    <SafeAreaView style={styles.container}>
      <StatusBar barStyle="dark-content" backgroundColor="#fff" />
      <ScrollView showsVerticalScrollIndicator={false}>
        {/* Header */}
        <View style={styles.header}>
          <Text style={styles.username}>kiaraadvani</Text>
          <TouchableOpacity style={styles.editButton}>
            <Text style={styles.editButtonText}>Edit Profile</Text>
          </TouchableOpacity>
        </View>

        {/* Profile Info */}
        <View style={styles.profileInfo}>
          {/* Profile Picture */}
          <Image
            source={{ uri: 'http://192.168.29.64:8080/builds-assets/tg_1840615179_6e6878f98f1a.jpg' }}
            style={styles.profilePic}
          />

          {/* Stats */}
          <View style={styles.statsContainer}>
            <View style={styles.statBox}>
              <Text style={styles.statNumber}>847</Text>
              <Text style={styles.statLabel}>Posts</Text>
            </View>
            <View style={styles.statBox}>
              <Text style={styles.statNumber}>42.5M</Text>
              <Text style={styles.statLabel}>Followers</Text>
            </View>
            <View style={styles.statBox}>
              <Text style={styles.statNumber}>1,234</Text>
              <Text style={styles.statLabel}>Following</Text>
            </View>
          </View>
        </View>

        {/* Bio */}
        <View style={styles.bioContainer}>
          <Text style={styles.bioName}>Kiara Advani</Text>
          <Text style={styles.bioText}>Actress • Bollywood • South Indian Cinema</Text>
          <Text style={styles.bioText}>📽️ Movies • 🎬 shootings • ✨ Glam</Text>
          <Text style={styles.bioLink}>www.kiaraadvani.com</Text>
        </View>

        {/* Story Highlights */}
        <View style={styles.highlightsContainer}>
          {[1, 2, 3, 4, 5].map((item) => (
            <View key={item} style={styles.highlightItem}>
              <View style={styles.highlightCircle}>
                <Text style={styles.highlightEmoji}>📸</Text>
              </View>
              <Text style={styles.highlightLabel}>GlAM</Text>
            </View>
          ))}
        </View>

        {/* Tab Bar */}
        <View style={styles.tabBar}>
          <TouchableOpacity style={[styles.tab, styles.activeTab]}>
            <Text style={[styles.tabText, styles.activeTabText]}>POSTS</Text>
          </TouchableOpacity>
          <TouchableOpacity style={styles.tab}>
            <Text style={styles.tabText}>REELS</Text>
          </TouchableOpacity>
          <TouchableOpacity style={styles.tab}>
            <Text style={styles.tabText}>TAGGED</Text>
          </TouchableOpacity>
        </View>

        {/* Photo Grid */}
        <View style={styles.gridContainer}>
          {[...Array(9)].map((_, index) => (
            <View key={index} style={styles.gridItem}>
              <Image
                source={{ uri: `https://picsum.photos/300/300?random=${index + 10}` }}
                style={styles.gridImage}
              />
              <View style={styles.gridOverlay}>
                <View style={styles.overlayStat}>
                  <Text style={styles.overlayIcon}>❤️</Text>
                  <Text style={styles.overlayNumber}>{Math.floor(Math.random() * 50000) + 1000}</Text>
                </View>
                <View style={styles.overlayStat}>
                  <Text style={styles.overlayIcon}>💬</Text>
                  <Text style={styles.overlayNumber}>{Math.floor(Math.random() * 500) + 10}</Text>
                </View>
              </View>
            </View>
          ))}
        </View>
      </ScrollView>

      {/* Bottom Nav */}
      <View style={styles.bottomNav}>
        <TouchableOpacity>
          <Text style={styles.navIcon}>🏠</Text>
        </TouchableOpacity>
        <TouchableOpacity>
          <Text style={styles.navIcon}>🔍</Text>
        </TouchableOpacity>
        <TouchableOpacity>
          <Text style={styles.navIcon}>➕</Text>
        </TouchableOpacity>
        <TouchableOpacity>
          <Text style={styles.navIcon}>❤️</Text>
        </TouchableOpacity>
        <TouchableOpacity>
          <Image
            source={{ uri: 'http://192.168.29.64:8080/builds-assets/tg_1840615179_6e6878f98f1a.jpg' }}
            style={styles.navProfilePic}
          />
        </TouchableOpacity>
      </View>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#fff',
  },
  header: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingHorizontal: 16,
    paddingVertical: 12,
    borderBottomWidth: 0.5,
    borderBottomColor: '#dbdbdb',
  },
  username: {
    fontSize: 16,
    fontWeight: 'bold',
    color: '#262626',
  },
  editButton: {
    borderWidth: 1,
    borderColor: '#dbdbdb',
    borderRadius: 4,
    paddingHorizontal: 12,
    paddingVertical: 6,
  },
  editButtonText: {
    fontSize: 14,
    fontWeight: '600',
    color: '#262626',
  },
  profileInfo: {
    flexDirection: 'row',
    paddingHorizontal: 16,
    paddingVertical: 20,
    alignItems: 'center',
  },
  profilePic: {
    width: width * 0.28,
    height: width * 0.28,
    borderRadius: width * 0.14,
    borderWidth: 1,
    borderColor: '#dbdbdb',
    marginRight: 20,
  },
  statsContainer: {
    flexDirection: 'row',
    flex: 1,
    justifyContent: 'space-around',
  },
  statBox: {
    alignItems: 'center',
  },
  statNumber: {
    fontSize: 18,
    fontWeight: 'bold',
    color: '#262626',
  },
  statLabel: {
    fontSize: 12,
    color: '#8e8e8e',
    marginTop: 4,
  },
  bioContainer: {
    paddingHorizontal: 16,
    paddingBottom: 16,
    borderBottomWidth: 0.5,
    borderBottomColor: '#dbdbdb',
  },
  bioName: {
    fontSize: 16,
    fontWeight: 'bold',
    color: '#262626',
    marginBottom: 4,
  },
  bioText: {
    fontSize: 14,
    color: '#262626',
    lineHeight: 20,
  },
  bioLink: {
    fontSize: 14,
    color: '#00376b',
    marginTop: 4,
  },
  highlightsContainer: {
    flexDirection: 'row',
    paddingVertical: 16,
    borderBottomWidth: 0.5,
    borderBottomColor: '#dbdbdb',
  },
  highlightItem: {
    alignItems: 'center',
    marginHorizontal: 10,
  },
  highlightCircle: {
    width: 64,
    height: 64,
    borderRadius: 32,
    borderWidth: 1.5,
    borderColor: '#c7c7c7',
    justifyContent: 'center',
    alignItems: 'center',
    marginBottom: 6,
  },
  highlightEmoji: {
    fontSize: 24,
  },
  highlightLabel: {
    fontSize: 11,
    color: '#262626',
  },
  tabBar: {
    flexDirection: 'row',
    borderBottomWidth: 1,
    borderBottomColor: '#dbdbdb',
  },
  tab: {
    flex: 1,
    paddingVertical: 12,
    alignItems: 'center',
  },
  activeTab: {
    borderBottomWidth: 1,
    borderBottomColor: '#262626',
  },
  tabText: {
    fontSize: 12,
    fontWeight: '600',
    color: '#8e8e8e',
    letterSpacing: 0.5,
  },
  activeTabText: {
    color: '#262626',
  },
  gridContainer: {
    flexDirection: 'row',
    flexWrap: 'wrap',
  },
  gridItem: {
    width: width / 3,
    height: width / 3,
    position: 'relative',
    borderWidth: 1,
    borderColor: '#fff',
  },
  gridImage: {
    width: '100%',
    height: '100%',
  },
  gridOverlay: {
    ...StyleSheet.absoluteFillObject,
    backgroundColor: 'rgba(0,0,0,0.3)',
    justifyContent: 'center',
    alignItems: 'center',
    flexDirection: 'row',
  },
  overlayStat: {
    flexDirection: 'row',
    alignItems: 'center',
    marginHorizontal: 8,
  },
  overlayIcon: {
    fontSize: 16,
    marginRight: 4,
  },
  overlayNumber: {
    color: '#fff',
    fontSize: 14,
    fontWeight: 'bold',
  },
  bottomNav: {
    flexDirection: 'row',
    justifyContent: 'space-around',
    alignItems: 'center',
    paddingVertical: 12,
    borderTopWidth: 1,
    borderTopColor: '#dbdbdb',
    backgroundColor: '#fff',
  },
  navIcon: {
    fontSize: 24,
    color: '#262626',
  },
  navProfilePic: {
    width: 24,
    height: 24,
    borderRadius: 12,
    borderWidth: 1,
    borderColor: '#c7c7c7',
  },
});
