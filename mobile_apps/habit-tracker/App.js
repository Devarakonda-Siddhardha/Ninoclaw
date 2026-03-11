import React, { useState } from 'react';
import { View, Text, TextInput, TouchableOpacity, FlatList, StyleSheet, SafeAreaView, StatusBar } from 'react-native';

export default function App() {
  const [habit, setHabit] = useState('');
  const [habits, setHabits] = useState([
    { id: 1, text: 'Drink 8 glasses of water', completed: false },
    { id: 2, text: 'Exercise for 30 mins', completed: true },
    { id: 3, text: 'Read for 20 mins', completed: false },
  ]);

  const addHabit = () => {
    if (habit.trim()) {
      setHabits([...habits, { id: Date.now(), text: habit, completed: false }]);
      setHabit('');
    }
  };

  const toggleHabit = (id) => {
    setHabits(habits.map(h => h.id === id ? { ...h, completed: !h.completed } : h));
  };

  const deleteHabit = (id) => {
    setHabits(habits.filter(h => h.id !== id));
  };

  const renderItem = ({ item }) => (
    <View style={[styles.habitItem, item.completed && styles.completedItem]}>
      <TouchableOpacity onPress={() => toggleHabit(item.id)} style={styles.habitContent}>
        <View style={[styles.checkbox, item.completed && styles.checkedBox]}>
          {item.completed && <Text style={styles.checkmark}>✓</Text>}
        </View>
        <Text style={[styles.habitText, item.completed && styles.completedText]}>{item.text}</Text>
      </TouchableOpacity>
      <TouchableOpacity onPress={() => deleteHabit(item.id)} style={styles.deleteBtn}>
        <Text style={styles.deleteText}>✕</Text>
      </TouchableOpacity>
    </View>
  );

  return (
    <SafeAreaView style={styles.container}>
      <StatusBar barStyle="dark-content" />
      <View style={styles.header}>
        <Text style={styles.title}>Habit Tracker</Text>
        <Text style={styles.subtitle}>Build better habits daily</Text>
      </View>

      <View style={styles.inputContainer}>
        <TextInput
          style={styles.input}
          placeholder="Add a new habit..."
          value={habit}
          onChangeText={setHabit}
        />
        <TouchableOpacity onPress={addHabit} style={styles.addBtn}>
          <Text style={styles.addBtnText}>+</Text>
        </TouchableOpacity>
      </View>

      <FlatList
        data={habits}
        renderItem={renderItem}
        keyExtractor={item => item.id.toString()}
        style={styles.list}
        contentContainerStyle={styles.listContent}
      />

      <View style={styles.footer}>
        <Text style={styles.stats}>{habits.filter(h => h.completed).length} / {habits.length} completed</Text>
      </View>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#f5f5f5',
  },
  header: {
    padding: 20,
    paddingTop: 40,
    backgroundColor: '#fff',
    borderBottomWidth: 1,
    borderBottomColor: '#e0e0e0',
  },
  title: {
    fontSize: 28,
    fontWeight: 'bold',
    color: '#333',
  },
  subtitle: {
    fontSize: 14,
    color: '#888',
    marginTop: 5,
  },
  inputContainer: {
    flexDirection: 'row',
    padding: 15,
    backgroundColor: '#fff',
  },
  input: {
    flex: 1,
    height: 50,
    borderWidth: 1,
    borderColor: '#ddd',
    borderRadius: 25,
    paddingHorizontal: 20,
    fontSize: 16,
    backgroundColor: '#f9f9f9',
  },
  addBtn: {
    width: 50,
    height: 50,
    borderRadius: 25,
    backgroundColor: '#6C63FF',
    marginLeft: 10,
    justifyContent: 'center',
    alignItems: 'center',
  },
  addBtnText: {
    fontSize: 24,
    color: '#fff',
    fontWeight: 'bold',
  },
  list: {
    flex: 1,
  },
  listContent: {
    padding: 15,
  },
  habitItem: {
    flexDirection: 'row',
    backgroundColor: '#fff',
    borderRadius: 12,
    padding: 15,
    marginBottom: 10,
    alignItems: 'center',
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 1 },
    shadowOpacity: 0.1,
    shadowRadius: 3,
    elevation: 2,
  },
  habitContent: {
    flex: 1,
    flexDirection: 'row',
    alignItems: 'center',
  },
  checkbox: {
    width: 24,
    height: 24,
    borderRadius: 12,
    borderWidth: 2,
    borderColor: '#6C63FF',
    marginRight: 12,
    justifyContent: 'center',
    alignItems: 'center',
  },
  checkedBox: {
    backgroundColor: '#6C63FF',
  },
  checkmark: {
    color: '#fff',
    fontSize: 14,
    fontWeight: 'bold',
  },
  habitText: {
    fontSize: 16,
    color: '#333',
    flex: 1,
  },
  completedItem: {
    opacity: 0.7,
  },
  completedText: {
    textDecorationLine: 'line-through',
    color: '#999',
  },
  deleteBtn: {
    padding: 8,
  },
  deleteText: {
    fontSize: 18,
    color: '#ff6b6b',
    fontWeight: 'bold',
  },
  footer: {
    padding: 20,
    backgroundColor: '#fff',
    borderTopWidth: 1,
    borderTopColor: '#e0e0e0',
    alignItems: 'center',
  },
  stats: {
    fontSize: 14,
    color: '#666',
    fontWeight: '600',
  },
});
