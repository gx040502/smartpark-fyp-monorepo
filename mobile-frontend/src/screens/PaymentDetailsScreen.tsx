import React from 'react';
import { View, Text, TouchableOpacity, ScrollView } from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import { NativeStackNavigationProp } from '@react-navigation/native-stack';
import { RouteProp } from '@react-navigation/native';
import { RootStackParamList } from '../navigation/AppNavigator';
import { ArrowLeft } from 'lucide-react-native';

type Props = {
  navigation: NativeStackNavigationProp<RootStackParamList, 'PaymentDetails'>;
  route: RouteProp<RootStackParamList, 'PaymentDetails'>;
};

export default function PaymentDetailsScreen({ navigation, route }: Props) {
  const insets = useSafeAreaInsets();
  const { sessionData } = route.params;

  const formatDate = (dateString: string) => {
    if (!dateString) return 'N/A';
    let normalized = dateString;
    if (!normalized.includes('T')) normalized = normalized.replace(' ', 'T');
    if (!normalized.endsWith('Z') && !normalized.includes('+')) normalized += 'Z';
    
    const date = new Date(normalized);
    // Add 8 hours for Malaysia Time
    const myTime = new Date(date.getTime() + (8 * 60 * 60 * 1000));
    
    const day = myTime.getUTCDate();
    const month = myTime.getUTCMonth() + 1;
    const year = myTime.getUTCFullYear();
    
    let hours = myTime.getUTCHours();
    const minutes = myTime.getUTCMinutes();
    const seconds = myTime.getUTCSeconds();
    
    const ampm = hours >= 12 ? 'PM' : 'AM';
    hours = hours % 12;
    hours = hours ? hours : 12;
    
    const minStr = minutes < 10 ? '0' + minutes : minutes;
    const secStr = seconds < 10 ? '0' + seconds : seconds;
    
    return `${month}/${day}/${year}, ${hours}:${minStr}:${secStr} ${ampm}`;
  };

  return (
    <View className="flex-1 bg-white" style={{ paddingTop: insets.top, paddingBottom: insets.bottom }}>
      {/* Header */}
      <View className="flex-row items-center px-4 py-3 border-b border-gray-100">
        <TouchableOpacity className="p-2" onPress={() => navigation.goBack()}>
          <ArrowLeft size={24} color="#333" />
        </TouchableOpacity>
        <Text className="font-interBold text-lg ml-2 text-gray-800">Payment Details</Text>
      </View>

      <ScrollView className="flex-1 px-6 pt-6">
        {/* Info Card */}
        <View className="bg-[#f9f9f9] rounded-xl p-5 mb-8 shadow-sm">
          <View className="flex-row justify-between mb-4 pb-4 border-b border-gray-200">
            <Text className="font-inter text-gray-500">License Plate</Text>
            <Text className="font-interBold text-gray-900">{sessionData.license_plate}</Text>
          </View>
          <View className="flex-row justify-between mb-4 pb-4 border-b border-gray-200">
            <Text className="font-inter text-gray-500">Color</Text>
            <Text className="font-interBold text-gray-900 capitalize">{sessionData.color || 'N/A'}</Text>
          </View>
          <View className="flex-row justify-between mb-4 pb-4 border-b border-gray-200">
            <Text className="font-inter text-gray-500">Brand</Text>
            <Text className="font-interBold text-gray-900 capitalize">{sessionData.model || 'N/A'}</Text>
          </View>
          <View className="flex-row justify-between">
            <Text className="font-inter text-gray-500">Entry Time</Text>
            <Text className="font-interBold text-gray-900">{formatDate(sessionData.entry_time)}</Text>
          </View>
        </View>

        {/* Total Due Section */}
        <View className="items-center mb-10">
          <Text className="font-inter text-gray-500 mb-2">Total Due</Text>
          <Text className="font-manrope text-5xl font-bold text-[#28a745]">
            ${Number(sessionData.amount_due).toFixed(2)}
          </Text>
        </View>
      </ScrollView>

      {/* Footer Actions */}
      <View className="px-6 py-4 flex-row space-x-4 bg-white border-t border-gray-100">
        <TouchableOpacity
          className="flex-1 h-[56px] bg-gray-100 rounded-lg items-center justify-center mr-2"
          onPress={() => navigation.goBack()}
        >
          <Text className="font-interBold text-gray-600 text-[16px]">Cancel</Text>
        </TouchableOpacity>
        <TouchableOpacity
          className="flex-1 h-[56px] bg-[#007BFF] rounded-lg items-center justify-center ml-2"
          style={{
            shadowColor: '#007BFF',
            shadowOffset: { width: 0, height: 4 },
            shadowOpacity: 0.2,
            shadowRadius: 8,
            elevation: 4,
          }}
          onPress={() => navigation.navigate('SelectMethod', { sessionData })}
        >
          <Text className="font-interBold text-white text-[16px]">Pay Now</Text>
        </TouchableOpacity>
      </View>
    </View>
  );
}
